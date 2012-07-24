##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """PingService
Class that provides a way to asynchronously ping (ICMP packets) IP addresses.
"""

import sys
import os
import time
import socket
import errno
import logging
log = logging.getLogger("zen.PingService")

# Zenoss custom ICMP library
from icmpecho.Ping import Ping4, Ping6

from twisted.internet import reactor, defer
from twisted.python.failure import Failure

import Globals
from Products.ZenStatus.PingJob import PingJob

class PermissionError(Exception):
    """Not permitted to access resource."""

class IpConflict(Exception):
    """Pinging two IP pingjobs simultaneously with different hostnames"""

class PingJobError(Exception):
    def __init__(self, error_message, ipaddr):
        Exception.__init__(self, error_message)
        self.ipaddr = ipaddr

class PingService(object):
    
    def __init__(self, protocol, timeout=2, defaultTries=2):
        self.reconfigure(timeout)
        self.procId = os.getpid()
        self.defaultTries = defaultTries
        self.jobqueue = {}
        self.pktdata = 'zenping %s %s' % (socket.getfqdn(), self.procId)

        self._protocol = protocol
        reactor.addReader(self)

    def reconfigure(self, timeout=2):
        self.timeout = timeout

    def fileno(self):
        """
        The reactor will do reads only if we support a file-like interface
        """
        return self._protocol.fileno()

    def logPrefix(self):
        """
        The reactor will do reads only if we support a file-like interface
        """
        return None

    def connectionLost(self, unused):
        reactor.removeReader(self)
        self._protocol.close()

    def ping(self, ip):
        """
        Ping the IP address and return the result in a deferred
        """
        if isinstance(ip, PingJob):
            pj = ip
        else:
            pj = PingJob(ip, maxtries=self.defaultTries)
        self._ping(pj)
        return pj.deferred

    def _ping(self, pingJob):
        """
        Take a pingjob and send an ICMP packet for it
        """
        try:
            family, sockaddr, echo_kwargs, socket_kwargs = \
                      pingJob.pingArgs()
            pingJob.start = self._protocol.send(sockaddr,
                                                socket_kwargs,
                                                echo_kwargs)
            pingJob.sent += 1

            reactor.callLater(self.timeout, self.checkTimeout, pingJob)
            current = self.jobqueue.get(pingJob.ipaddr, None)
            if current and pingJob.hostname != current.hostname:
                raise IpConflict("Host %s and %s are both using IP %s" %
                                     (pingJob.hostname,
                                      current.hostname,
                                      pingJob.ipaddr))
            self.jobqueue[pingJob.ipaddr] = pingJob
        except Exception, e:  # Note: sockets with bad addresses fail
            log.debug("%s sendto error %s" % (pingJob.ipaddr, e))
            self.pingJobFail(pingJob)

    def _processPacket(self, reply):
        """
        Examine the parsed reply and determine what to do with it.
        """
        sourceIp = reply['address']
        pj = self.jobqueue.get(sourceIp)
        if reply['alive'] and pj:
            pj.rcvCount += 1
            pj.rtt = time.time() - pj.start
            pj.results.append(pj.rtt)
            log.debug("%d bytes from %s: icmp_seq=%d time=%0.3f ms",
                      reply['data_size'], sourceIp, reply['sequence'],
                      pj.rtt * 1000)

            if pj.rcvCount >= pj.sampleSize:
                self.pingJobSucceed(pj)
            else:
                self._ping(pj)

        elif not reply['alive'] and pj:
            log.debug("ICMP unreachable message for %s", pj.ipaddr)
            self.pingJobFail(pj)
            
        #else:
            #log.debug("Unexpected ICMP packet %s %s", sourceIp, reply)

    def doRead(self):
        """
        Receive packets from the socket and process them.

        The name is required by the reactor select() functionality
        """
        try:
            for reply, sockaddr in self._protocol.receive():
                if not reactor.running:
                    return
                self._processPacket(reply)
        except socket.error, err:
            errnum, errmsg = err.args
            if errnum == errno.EAGAIN:
                return
            raise err
        except Exception, ex:
            log.exception("Error while receiving packet: %s" % ex)

    def pingJobSucceed(self, pj):
        """
        PingJob completed successfully.
        """
        pj.message = "IP %s is up" % pj.ipaddr
        pj.severity = 0
        self.dequePingJob(pj)
        if not pj.deferred.called:
            pj.deferred.callback(pj)

    def pingJobFail(self, pj):
        """
        PingJob has failed --  remove from jobqueue.
        """
        pj.rtt = -1
        pj.message = "IP %s is down" % pj.ipaddr
        self.dequePingJob(pj)
        if not pj.deferred.called:
            pj.deferred.errback(Failure(PingJobError(pj.message, pj.ipaddr)))

    def dequePingJob(self, pj):
        try:
            del self.jobqueue[pj.ipaddr]
        except KeyError:
            pass

    def checkTimeout(self, pj):
        if pj.ipaddr in self.jobqueue:
            runtime = time.time() - pj.start
            if runtime > self.timeout:
                pj.loss += 1
                log.debug("%s pingjob timeout on attempt %d (timeout=%ss, max tries=%s)",
                           pj.ipaddr, pj.loss, self.timeout, pj.maxtries)
                if pj.loss >= pj.maxtries:
                    self.pingJobFail(pj)
                else:
                    self._ping(pj)
            else:
                log.debug("Calling checkTimeout needlessly for %s", pj.ipaddr)

    def jobCount(self):
        return len(self.jobqueue)


def _printResults(results, start):
    good = [pj for s, pj in results if s and pj.rtt >= 0]
    bad = [pj for s, pj in results if s and pj.rtt < 0]
    if good: print "Good IPs: %s" % " ".join(g.ipaddr for g in good)
    if bad: print "Bad IPs: %s" % " ".join(b.ipaddr for b in bad)
    print "Tested %d IPs in %.2f seconds" % (len(results), time.time() - start)
    reactor.stop()

if __name__ == "__main__":
    # Sockets are injected into the main module by pyraw
    # pyraw PingService.py [ip_addresses]

    protocol = Ping4(IPV4_SOCKET)
    ping = PingService(protocol)
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(10)
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = ("127.0.0.1",)
    lst = defer.DeferredList(map(ping.ping, targets), consumeErrors=True)
    lst.addCallback(_printResults, time.time())
    reactor.run()
