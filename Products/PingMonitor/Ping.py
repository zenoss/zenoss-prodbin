#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import sys
import os
import types
import time
import logging
import select
import socket
import ip
import icmp
import pprint


class PingJob:
    """
    Class representing a single target to be pinged.
    """
    def __init__(self, address, hostname="", url="", pingStatus=0):
        self.address = address 
        self.hostname = hostname
        self.url = url
        self.pingStatus = pingStatus
        self.rtt = 0
        self.start = 0
        self.end = 0
        self.sent = 0
        self.message = ""
        self.severity = 3
        self.type = 1





class Ping(object):    
    """
    Class that provides syncronous icmp ping.
    """

    def __init__(self, tries=2, timeout=2, chunkSize=10):
        self.tries = tries
        self.timeout = timeout
        self.chunkSize = chunkSize
        self.procId = os.getpid()
        self.jobqueue = {}
        self.createPingSocket()


    def __del__(self):
        self.closePingSocket()


    def createPingSocket(self):
        """make an ICMP socket to use for sending and receiving pings"""
        family = socket.AF_INET
        type = socket.SOCK_RAW
        proto = socket.IPPROTO_ICMP
        sock = socket.socket(family, type, proto)
        sock.setblocking(0)
        self.pingsocket = sock


    def closePingSocket(self):
        """unregister poll and close socket"""
        self.pingsocket.close()

    
    def sendPackets(self, numbtosend):
        """send numbtosend number of pingJobs and re"""
        for i in range(numbtosend):
            if self.sendqueue: 
                pingJob = self.sendqueue.pop()
                self.sendPacket(pingJob)
            

    def sendPacket(self, pingJob):
        """Take a pingjob and send an ICMP packet for it"""
        pkt = icmp.Packet()
        pkt.type = icmp.ICMP_ECHO
        pkt.id = self.procId
        pkt.seq = pingJob.sent
        pkt.data = 'Confmon connectivity test'
        buf = pkt.assemble()
        pingJob.start = time.time()
        logging.debug("send icmp to '%s'", pingJob.address)
        #### sockets with bad addresses fail
        try:
            self.pingsocket.sendto(buf, (pingJob.address, 0))
        except SystemExit: raise
        except:
            pingJob.rtt = -1
            pingJob.message = "%s error sending to socket" % pingJob.address
            if hasattr(self, "reportPingJob"):
                self.reportPingJob(pingJob)
        pingJob.sent = pkt.seq + 1
        self.jobqueue[pingJob.address] = pingJob


    def recvPacket(self):
        """receive a packet and decode its header"""
        data = self.pingsocket.recv(4096)
        if data:
            ipreply = ip.Packet(data)
            icmppkt = icmp.Packet(ipreply.data)
            sourceip =  ipreply.src
            logging.debug("received ip = %s id = %s" % (sourceip,icmppkt.id))
            if (icmppkt.id == self.procId and 
                self.jobqueue.has_key(sourceip)):
                pingJob = self.jobqueue[sourceip]
                pingJob.rtt = time.time() - pingJob.start
                pingJob.message = "%s is now reachable" % pingJob.hostname
                del self.jobqueue[sourceip]
                if hasattr(self, "reportPingJob"):
                    self.reportPingJob(pingJob)
            else:
                logging.debug("got unexpected packet from %s" % sourceip)


    def checkTimeouts(self):
        """check to see if pingJobs in jobqueue have timed out"""
        joblist = self.jobqueue.values()
        for pingJob in joblist:
            if time.time() - pingJob.start > self.timeout:
                if pingJob.sent >= self.tries:
                    pingJob.rtt = -1
                    pingJob.message = "%s is unreachable" % pingJob.hostname 
                    del self.jobqueue[pingJob.address]
                    if hasattr(self, "reportPingJob"):
                        self.reportPingJob(pingJob)
                    self.sendPackets(1)
                else:
                    self.sendPacket(pingJob)


    def eventLoop(self, devices):
        startLoop = time.time()
        logging.info("starting ping cycle %s" % (time.asctime()))
        self.sendqueue = devices.values()
        self.createPingSocket()
        self.sendPackets(self.chunkSize)
        while len(self.sendqueue) or len(self.jobqueue):
            while 1:
                data = select.select([self.pingsocket,], [], [], 0.001)
                if data[0]:
                    self.recvPacket()
                    self.sendPackets(1)
                else:
                    break
            self.checkTimeouts()
        self.closePingSocket()
        logging.info("ping cycle complete %s" % (time.asctime()))
        runtime = time.time() - startLoop
        logging.info("pinged %d devices in %3.2f seconds" % 
                    (len(devices), runtime))
        return runtime
    

    def ping(self, ips):
        """Perform async ping of a list of ips returns (goodips, badips).
        """
        if type(ips) == types.StringType: ips = (ips,)
        devices = {}
        for ip in ips: devices[ip] = PingJob(ip)
        self.eventLoop(devices)
        goodips = []
        badips = []
        for pj in devices.values():
            if pj.rtt >= 0: goodips.append(pj.address)
            else: badips.append(pj.address)
        return (goodips, badips)
            

    
if __name__ == "__main__":
    ping = Ping()
    if len(sys.argv) > 1: targets = sys.argv[1:]
    else: targets = ("127.0.0.1",)
    pprint.pprint(ping.ping(targets))
