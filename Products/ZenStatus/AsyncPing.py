#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import sys
import os
import types
import time
import select
import socket
import ip
import icmp
import errno
import pprint
import logging
log = logging.getLogger("zen.Ping")

from twisted.internet import reactor, defer
from sets import Set

class PermissionError(Exception):
    """Not permitted to access resource."""


class PingJob:
    """
    Class representing a single target to be pinged.
    """
    def __init__(self, ipaddr, hostname="", status=0, unused_cycle=60):
        self.ipaddr = ipaddr 
        self.hostname = hostname
        self.status = status
        self.reset()


    def reset(self):
        self.deferred = defer.Deferred()
        self.parent = False
        self.rrt = 0
        self.start = 0
        self.sent = 0
        self.message = ""
        self.severity = 5
        self.inprocess = False
        self.pathcheck = 0
        self.eventState = 0


    def checkpath(self):
        if self.parent:
            return self.parent.checkpath()


    def routerpj(self):
        if self.parent:
            return self.parent.routerpj()


plog = logging.getLogger("zen.Ping")
class Ping(object):    
    """
    Class that provides asyncronous icmp ping.
    """
    
    def __init__(self, tries=2, timeout=2, chunkSize=10):
        self.tries = tries
        self.timeout = timeout
        self.chunkSize = chunkSize
        self.procId = os.getpid()
        self.jobqueue = {}
        self.pingsocket = None
        self.morepkts = True
        self.devcount = 0
        self.createPingSocket()
        self.pktdata = 'zenping %s %s' % (socket.getfqdn(), self.procId)
        self.incount = self.outcount = 0

    def createPingSocket(self):
        """make an ICMP socket to use for sending and receiving pings"""
        try:
            s = socket
            self.pingsocket = s.socket(s.AF_INET, s.SOCK_RAW, s.IPPROTO_ICMP)
            self.pingsocket.setblocking(0)
            reactor.addReader(self)
        except socket.error, e:
            err, msg = e.args
            if err == errno.EACCES:
                raise PermissionError("must be root to send icmp.")
            raise e

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
        """Take a pingjob and send an ICMP packet for it"""
        #### sockets with bad addresses fail
        try:
            pkt = icmp.Packet()
            pkt.type = icmp.ICMP_ECHO
            pkt.id = self.procId
            pkt.seq = pingJob.sent
            pkt.data = self.pktdata 
            buf = pkt.assemble()
            pingJob.start = time.time()
            plog.debug("send icmp to '%s'", pingJob.ipaddr)
            reactor.callLater(self.timeout, self.checkTimeout, pingJob)
            self.pingsocket.sendto(buf, (pingJob.ipaddr, 0))
            pingJob.sent += 1 
            self.jobqueue[pingJob.ipaddr] = pingJob
        except (SystemExit, KeyboardInterrupt): raise
        except Exception, e:
            pingJob.rtt = -1
            pingJob.message = "%s sendto error %s" % (pingJob.ipaddr, e)
            self.reportPingJob(pingJob)


    def recvPackets(self):
        """receive a packet and decode its header"""
        while 1:
            try:
                data, (host, port) = self.pingsocket.recvfrom(1024)
                if not data: return
                ipreply = ip.Packet(data)
                icmppkt = icmp.Packet(ipreply.data)
                sip =  ipreply.src
                if (icmppkt.type == icmp.ICMP_ECHOREPLY and 
                    icmppkt.id == self.procId and
                    self.jobqueue.has_key(sip)):
                    plog.debug("echo reply pkt %s %s", sip, icmppkt)
                    self.pingJobSucceed(self.jobqueue[sip])
                elif icmppkt.type == icmp.ICMP_UNREACH:
                    try:
                        origpkt = ip.Packet(icmppkt.data)
                        origicmp = icmp.Packet(origpkt.data)
                        dip = origpkt.dst
                        plog.debug("host unreachable pkt %s", dip)
                        if (origicmp.data == self.pktdata 
                            and self.jobqueue.has_key(dip)):
                            self.pingJobFail(self.jobqueue[dip])
                    except ValueError:
                        plog.warn("failed to parse host unreachable packet")
                else:
                    plog.debug("unexpected pkt %s %s", sip, icmppkt)
            except (SystemExit, KeyboardInterrupt): raise
            except socket.error, err:
                err, errmsg = err.args
                if err == errno.EAGAIN:
                    return
                raise err
            except Exception, ex:
                log.exception("receiving packet error: %s" % ex)


    def pingJobSucceed(self, pj):
        """PingJob completed successfully.
        """
        plog.debug("pj succeed for %s", pj.ipaddr)
        pj.rtt = time.time() - pj.start
        pj.message = "%s ip %s is up" % (pj.hostname, pj.ipaddr)
        self.reportPingJob(pj)


    def pingJobFail(self, pj):
        """PingJob has failed remove from jobqueue.
        """
        plog.debug("pj fail for %s", pj.ipaddr)
        pj.rtt = -1
        pj.message = "%s ip %s is down" % (pj.hostname, pj.ipaddr) 
        self.reportPingJob(pj)

    def reportPingJob(self, pj):
        del self.jobqueue[pj.ipaddr]
        if not pj.deferred.called:
            pj.deferred.callback(pj)

    def checkTimeout(self, pj):
        if self.jobqueue.has_key(pj.ipaddr):
            now = time.time()
            if now - pj.start > self.timeout:
                if pj.sent >= self.tries:
                    plog.debug("pj timeout for %s", pj.ipaddr)
                    self.pingJobFail(pj)
                else:
                    self.sendPacket(pj)

    def ping(self, ip):
        """Perform async ping of a list of ips returns (goodips, badips).
        """
        pj = PingJob(ip)
        self.sendPacket(pj)
        return pj.deferred

def _printResults(results, start):
    good = [pj for s, pj in results if s and pj.rtt >= 0]
    bad = [pj for s, pj in results if s and pj.rtt < 0]
    if good: print "Good ips: %s" % " ".join([g.ipaddr for g in good])
    if bad: print "Bad ips: %s" % " ".join([b.ipaddr for b in bad])
    print "Tested %d ips in %.1f seconds" % (len(results), time.time() - start)
    reactor.stop()

if __name__ == "__main__":
    ping = Ping()
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    if len(sys.argv) > 1: targets = sys.argv[1:]
    else: targets = ("127.0.0.1",)
    lst = defer.DeferredList(map(ping.ping, targets), consumeErrors=True)
    lst.addCallback(_printResults, time.time())
    reactor.run()
