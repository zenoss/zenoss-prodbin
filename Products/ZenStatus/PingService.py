###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys
import os
import time
import socket
import ip
import icmp
import errno
import logging
log = logging.getLogger("zen.PingService")

from twisted.internet import reactor, defer

import Globals
from Products.ZenStatus.PingJob import PingJob

class PermissionError(Exception):
    """Not permitted to access resource."""

class IpConflict(Exception):
    """Pinging two jobs simultaneously with different hostnames but the same IP"""


class PingService(object):    
    """
    Class that provides asynchronous ping (ICMP packets) capability.
    """
    
    def __init__(self, timeout=2, sock=None, defaultTries=2):
        self.reconfigure(timeout)
        self.procId = os.getpid()
        self.defaultTries = defaultTries
        self.jobqueue = {}
        self.pktdata = 'zenping %s %s' % (socket.getfqdn(), self.procId)
        self.createPingSocket(sock)

    def reconfigure(self, timeout=2):
        self.timeout = timeout

    def createPingSocket(self, sock):
        """make an ICMP socket to use for sending and receiving pings"""
        socketargs = socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP
        if sock is None:
            try:
                s = socket
                self.pingsocket = s.socket(*socketargs)
            except socket.error, e:
                err, msg = e.args
                if err == errno.EACCES:
                    raise PermissionError("Must be root to send ICMP packets.")
                raise e
        else:
            self.pingsocket = socket.fromfd(sock, *socketargs)
            os.close(sock)
        self.pingsocket.setblocking(0)
        reactor.addReader(self)

    def fileno(self):
        return self.pingsocket.fileno()

    def doRead(self):
        self.recvPackets()

    def connectionLost(self, unused):
        reactor.removeReader(self)
        self.pingsocket.close()

    def logPrefix(self):
        return None

    def sendPacket(self, pingJob):
        """
        Take a pingjob and send an ICMP packet for it
        """
        #### sockets with bad addresses fail
        try:
            pkt = icmp.Echo(self.procId, pingJob.sent, self.pktdata)
            buf = icmp.assemble(pkt)
            pingJob.start = time.time()
            self.pingsocket.sendto(buf, (pingJob.ipaddr, 0))
            reactor.callLater(self.timeout, self.checkTimeout, pingJob)
            pingJob.sent += 1
            current = self.jobqueue.get(pingJob.ipaddr, None)
            if current:
                if pingJob.hostname != current.hostname:
                    raise IpConflict("Host %s and %s are both using IP %s" %
                                     (pingJob.hostname,
                                      current.hostname,
                                      pingJob.ipaddr))
            self.jobqueue[pingJob.ipaddr] = pingJob
        except Exception, e:
            pingJob.rtt = -1
            pingJob.message = "%s sendto error %s" % (pingJob.ipaddr, e)
            self.dequePingJob(pingJob)

    def recvPackets(self):
        """receive a packet and decode its header"""
        while reactor.running:
            try:
                data, (host, port) = self.pingsocket.recvfrom(1024)
                if not data: return
                ipreply = ip.disassemble(data)
                try:
                    icmppkt = icmp.disassemble(ipreply.data)
                except ValueError:
                    log.debug("Checksum failure on packet %r", ipreply.data)
                    try:
                        icmppkt = icmp.disassemble(ipreply.data, 0)
                    except ValueError:
                        continue            # probably Unknown type
                except Exception, ex:
                    log.debug("Unable to decode reply packet payload %s", ex)
                    continue
                sip =  ipreply.src
                if (icmppkt.get_type() == icmp.ICMP_ECHOREPLY and 
                    icmppkt.get_id() == self.procId and
                    sip in self.jobqueue):
                    pj = self.jobqueue[sip]
                    pj.rcvCount += 1
                    pj.rtt = time.time() - pj.start
                    pj.results.append(pj.rtt)
                    log.debug("%d bytes from %s: icmp_seq=%d time=%0.3f ms",
                               len(icmppkt.get_data()), sip, icmppkt.get_seq(),
                               pj.rtt * 1000)
                    if pj.rcvCount >= pj.sampleSize:
                        self.pingJobSucceed(pj)
                    else:
                        self.sendPacket(pj)

                elif icmppkt.get_type() == icmp.ICMP_UNREACH:
                    try:
                        origpkt = icmppkt.get_embedded_ip()
                        dip = origpkt.dst
                        if (origpkt.data.find(self.pktdata) > -1
                            and self.jobqueue.has_key(dip)):
                            log.debug("ICMP unreachable message for %s", dip)
                            self.pingJobFail(self.jobqueue[dip])
                    except ValueError, ex:
                        log.warn("Failed to parse host unreachable packet")
                #else:
                    #log.debug("Unexpected pkt %s %s", sip, icmppkt)
            except socket.error, err:
                errnum, errmsg = err.args
                if errnum == errno.EAGAIN:
                    return
                raise err
            except Exception, ex:
                log.exception("Error while receiving packet: %s" % ex)

    def pingJobSucceed(self, pj):
        """PingJob completed successfully.
        """
        pj.message = "IP %s is up" % (pj.ipaddr)
        pj.severity = 0
        self.dequePingJob(pj)

    def pingJobFail(self, pj):
        """PingJob has failed --  remove from jobqueue.
        """
        pj.rtt = -1
        pj.message = "IP %s is down" % (pj.ipaddr)
        self.dequePingJob(pj)

    def dequePingJob(self, pj):
        try:
            del self.jobqueue[pj.ipaddr]
        except KeyError:
            pass
        if not pj.deferred.called:
            pj.deferred.callback(pj)

    def checkTimeout(self, pj):
        if pj.ipaddr in self.jobqueue:
            runtime = time.time() - pj.start
            if runtime > self.timeout:
                pj.loss += 1
                log.debug("%s pingjob timeout on attempt %d (%s sec)",
                           pj.ipaddr, pj.loss, self.timeout)
                if pj.loss >= pj.maxtries:
                    self.pingJobFail(pj)
                else:
                    self.sendPacket(pj)
            else:
                log.debug("Calling checkTimeout needlessly for %s", pj.ipaddr)

    def jobCount(self):
        return len(self.jobqueue)

    def ping(self, ip):
        "Ping the IP address and return the result in a deferred"
        pj = PingJob(ip, maxtries=self.defaultTries)
        self.sendPacket(pj)
        return pj.deferred


def _printResults(results, start):
    good = [pj for s, pj in results if s and pj.rtt >= 0]
    bad = [pj for s, pj in results if s and pj.rtt < 0]
    if good: print "Good IPs: %s" % " ".join([g.ipaddr for g in good])
    if bad: print "Bad IPs: %s" % " ".join([b.ipaddr for b in bad])
    print "Tested %d IPs in %.1f seconds" % (len(results), time.time() - start)
    reactor.stop()

if __name__ == "__main__":
    ping = PingService()
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    if len(sys.argv) > 1: targets = sys.argv[1:]
    else: targets = ("127.0.0.1",)
    lst = defer.DeferredList(map(ping.ping, targets), consumeErrors=True)
    lst.addCallback(_printResults, time.time())
    reactor.run()
