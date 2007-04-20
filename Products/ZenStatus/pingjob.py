###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/
''' pingmonitor
creates a queue of hosts to be pinged (jobs),
and pings them until they respond, or the
maximum number of pings has been sent. After
sending out all these pings, we loop in a
receive function processing everything we get
back'''

import socket
import ip
import icmp
import os
import pprint
import time
import select
import sys

class PingJob:
    '''Class representing a single
    target to be pinged'''

    def __init__(self,host):
        self._host = host
        self._rtt = 0
        self._start = 0
        self._end = 0
        self._sent = 0

    def reset(self):
        self._rtt = 0
        self._start = 0
        self._end = 0
        self._sent = 0

    def getOrSet(self, attr, value=None):
        if value:
            setattr(self, attr, value)
        else:
            return getattr(self, attr)

    def host(self, value=None):
        return self.getOrSet('_host', value)

    def rtt(self, value=None):
        return self.getOrSet('_rtt', value)

    def start(self, value=None):
        return self.getOrSet('_start', value)

    def end(self, value=None):
        return self.getOrSet('_end', value)

    def sent(self, value=None):
        return self.getOrSet('_sent', value)

class PingMonitor:
    def __init__(self, timeout=0.25, tries=3, chunk=25):
        self._jobQueue = {}
        self._resultQueue = []
        self._id = os.getpid()
        self._timeOut = timeout
        self._tries = tries
        self._chunkSize = chunk
        self._socket = self._createSocket()

    def _createSocket(self):
        family = socket.AF_INET
        type = socket.SOCK_RAW
        proto = socket.IPPROTO_ICMP
        sock = socket.socket(family, type, proto)
        sock.setblocking(1)
        return sock

    def _setQueue(self, queueDict):
        self._jobQueue = queueDict

    def addTarget(self, target):
        try:
            target = socket.gethostbyname(target)
        except:
            pass
        self._jobQueue[target] = PingJob(target)

    def sendPings(self, queue):
        for target in self._jobQueue.values():
            self.sendPacket(target, queue)

    def recvPings(self, queue):
        timeOut = self._timeOut
        startTime = time.time()
        while 1:
            rd = select.select(
                [self._socket],
                [],
                [],
                self._timeOut)
            if rd[0]:
                (icmppkt, ippkt) = self.recvPacket()
                source =  ippkt.src
                if queue.has_key(source):
                    jobObj = queue[source]
                    jobObj.end(time.time())
                    jobObj.rtt(
                        jobObj.end() - jobObj.start())
                    self._resultQueue.append(jobObj)
                    del queue[source]
            timeOut = (startTime + self._timeOut) - time.time()
            if (not len(queue.keys())
                or timeOut < 0):
                    # loop everything in job queue
                    # move everything whose _sent is greater
                    # than or equal to _tries to result queue
                    # as failure
                    for item in queue.values():
                        if item.sent() >= self._tries:
                            item.rtt(0.0)
                            self._resultQueue.append(item)
                            del queue[item.host()]
                    break

    def sendPacket(self, target, queue):
        pkt = icmp.Packet()
        pkt.type = icmp.ICMP_ECHO
        pkt._id = self._id
        pkt.seq = target.sent()
        pkt.data = 'Confmon connectivity test'
        buf = pkt.assemble()
        target.start(time.time())
        #### sockets with bad addresses fail
        try:
            self._socket.sendto(buf, (target.host(), 0))
        except:
            target.rtt(0.0)
            self._resultQueue.append(target)
            del queue[target.host()]
        target.sent(pkt.seq + 1)

    def recvPacket(self):
        data = self._socket.recv(4096)
        if data:
            ipreply = ip.Packet(data)
            try:
                reply = icmp.Packet(ipreply.data)
            except:
                return
            return (reply, ipreply)

    def display(self):
        for result in self._resultQueue:
            if result.rtt() == 0.0:
                print "Host %s :: Sent %s :: FAILED" % (
                    result.host(),
                    result.sent())
            else:
                print "Host %s :: Sent %s :: RTT %s" % (
                    result.host(),
                    result.sent(),
                    result.rtt())

    def setTargets(self, chunk):
        '''set jobQueue = chunks
        remove good pings,
        leave bad pings until
        exceed _tries'''
        for ping in self._jobQueue.values():
            if ping.sent() >= self._tries:
                ping.rtt(0.0)
                del self._jobQueue[ping.host()]
                self._resultQueue.append(ping)

        for target in chunk:
            self._jobQueue[target] = PingJob(target)
            
    def _getChunk(self):
        chunk = {}
        targets = self._jobQueue.values()
        print len(targets), "LEN"
        print len(targets) % self._chunkSize
        if len(targets) % self._chunkSize:
            for None in range(len(targets) % self._chunkSize):
                t = targets.pop()
                chunk[t.host()] = t
        else:
            while targets:
                for None in range(self._chunkSize):
                    t = targets.pop()
                    chunk[t.host()] = t
        return chunk
        
    def run(self, targets):
        '''put failed targets into result queue
        loop over chunks and call doChunk
        for each'''
        
        self.setTargets(targets)
        while 1:
            chunk = self._getChunk()
            if not chunk:
                break
            else:
                print "HERE"
                # overwriting with one target...
                self.sendPings(chunk)
                self.recvPings(chunk)


if __name__=='__main__':
    # make sure we have wall time on windows
    if sys.platform == 'win32':
        time.time = time.clock

    fp = open(sys.argv[1],'r')
    startTime = time.time()
    targets = []
    x = PingMonitor(chunk=2)
    for target in fp.readlines():
        targets.append(target[:-1])
    x.run(targets)
    x.display()
    endTime=time.time()
    print endTime-startTime
