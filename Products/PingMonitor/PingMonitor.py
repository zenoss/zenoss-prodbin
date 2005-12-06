#!/usr/bin/env python2.1

#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__=''' PingMonitor

creates a queue of hosts to be pinged (jobs),
and pings them until they respond, or the
maximum number of pings has been sent. After
sending out all these pings, we loop in a
receive function processing everything we get
back

$Id: PingMonitor.py,v 1.70 2004/04/22 20:54:23 edahl Exp $'''

__version__ = "$Revision: 1.70 $"[11:-2]

import socket
import ip
import icmp
import os
import time
import select
import sys
import xmlrpclib
import logging

import Globals # make zope imports work

from Products.ZenUtils.Utils import parseconfig, basicAuthUrl
from StatusMonitor import StatusMonitor

class PingMonitor(StatusMonitor):

    ncoClass = "/Status/Ping"
    ncoAgent = "PingMonitor"
    ncoAlertGroup = "Ping"

    def __init__(self):
        StatusMonitor.__init__(self)
        self.pingconfsrv = self.options.zopeurl
        self.username = self.options.zopeusername
        self.password = self.options.zopepassword
        self.ncoserver = self.options.netcool 
        self.timeout = 1.2
        self.pingtries = 3
        self.cycleFailWarn = 0
        self.cycleFailCritical = 0
        self.chunkSize = 50
        self.cycleInterval = 60
        self.configCycleInterval = 20
        self.procId = os.getpid()
        self.configTime = 0
        self.jobqueue = {}
        self.goodDevices = {}
        self.badDevices = {}
        self.sendqueue = []
        self.procId = os.getpid()
        self.pingth = None
        #self.createPingSocket()


    def validConfig(self):
        """let getConfig know if we have a working config or not"""
        return self.goodDevices


    def loadConfig(self):
        "get the config data from file or server"
        if time.time()-self.configTime > self.configCycleInterval*60:
            confsrc = self.pingconfsrv or self.options.devicefile
            self.log.info("Reloading configuration from %s" % confsrc)
            if self.pingconfsrv:
                url = basicAuthUrl(self.username, self.password, 
                                    self.pingconfsrv)
                server = xmlrpclib.Server(url)
                self.timeout = server.getTimeOut()
                self.pingtries = server.getTries()
                self.cycleFailWarn = server.getCycleFailWarn()
                self.cycleFailCritical = server.getCycleFailCritical()
                self.chunkSize = server.getChunk()
                self.cycleInterval = server.getCycleInterval()
                self.configCycleInterval = server.getConfigCycleInterval() 
                self.maxFailures = server.getMaxFailures()
                devices = server.getPingDevices()
                self.prepDevices(devices)
            else:
                # load configuration from files
                self.timeout = float(self.options.timeout)
                self.pingtries = int(self.options.numbtries)
                self.cycleFailWarn = int(self.options.cyclefailwarn)
                self.cycleFailCritical = int(self.options.cyclefailcritical)
                self.chunkSize = int(self.options.chunksize)
                self.cycleInterval = int(self.options.cycle)
                self.configCycleInterval = int(self.options.configcycle)
                self.prepDevices(self.loadDevices(self.options.devicefile))
            self.configTime = time.time()


    def prepDevices(self, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            hostname, ip, url, pingStatus = device
            self.log.debug("got %s %s %s %s" % (hostname,ip,url,pingStatus))
            # resolve hostnames to ipaddresses
            try:
                if not ip:
                    ip = self.forwardDnsLookup(hostname)
                if pingStatus >= self.maxFailures:
                    self.log.debug("add %s to bad devices ping list" % hostname)
                    self.badDevices[ip] = PingJob(ip,hostname,
						url,pingStatus)
                else:
                    self.log.debug("add %s to main ping list" % hostname)
                    self.goodDevices[ip] = PingJob(ip, hostname,
						url, pingStatus)
            except socket.error: 
                message = "%s is unresolvable in dns" % hostname
                self.log.warn(message)
                try:
                    url = basicAuthUrl(self.username, self.password, url)
                    devsrv = xmlrpclib.Server(url)
                    devsrv.setPingStatus(-2)
                    if self.ncoserver:
                        ip = ''
                        pj = PingJob(ip, hostname, url, pingStatus)
                        pj.message = message
                        pj.rtt = -1
                        pj.type = 1
                        pj.severity = 3
                        self._sendEvent(pj)
                except SystemExit: raise
                except:
                    self.log.warn("problem sending dns failure event")

        #ping the devices that are over maxFailures once every config cycle
        if self.badDevices:
            self.log.info("checking devices with over %d failures" 
                            % self.maxFailures)
            self.eventLoop(self.badDevices)


    def loadDevices(self, devicefile):
        """load device list from file instead of zope config server"""
        lines = open(devicefile).readlines()
        linenumb = 0
        devices = []
        for line in lines:
            linenumb += 1
            hostname = line.strip()
            devices.append((hostname,None,'',-1))
        return devices
       

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


    def reportPingJob(self, pingJob):
        """send pingJob status information to DMD and optimon servers"""
        try:
            hostname = pingJob.hostname
            self.log.debug("processing PingJob for %s" % hostname)
            # device has never been pinged
            if pingJob.pingStatus < 0:
                self.log.debug("reset ping status on %s" % hostname)
                pingJob.pingStatus = 0

            # ping attempt failed
            if pingJob.rtt == -1:
                if (pingJob.url 
                    and not self._checkManageInt(hostname)):
                    self.log.debug("incr ping status on %s" % hostname)
    
                if (self.ncoserver 
                    and pingJob.pingStatus >= self.cycleFailWarn
                    and pingJob.pingStatus <= self.maxFailures):
                    if pingJob.pingStatus >= self.cycleFailCritical:
                        pingJob.severity = 5
                    else:
                        pingJob.severity = 3
                    self.log.warn("%s Ping Status = %d" % 
                        (pingJob.message, pingJob.pingStatus))
                    pingJob.type = 1
                    self._sendEvent(pingJob)
                else:
                    self.log.debug("%s no event sent Ping Status = %d" % 
                        (pingJob.message, pingJob.pingStatus))
                stat = pingJob.pingStatus + 1
                pingJob.pingStatus = stat
            else:
                # device was down but is back up
                if pingJob.pingStatus > 0:
                    if (self.ncoserver
                        and (pingJob.pingStatus >= self.cycleFailWarn
                        or pingJob.pingStatus >= self.cycleFailCritical)):
                        pingJob.severity = 0
                        pingJob.type = 2
                        self._sendEvent(pingJob)
                    pingJob.pingStatus = 0
                    if pingJob.pingStatus >= self.maxFailures:
                        pingJob.pingStatus = 0
                    self.log.info(pingJob.message)
                self.log.debug(pingJob.message)
        except SystemExit: raise
        except:
            self.log.exception(
                "unable to contact zope for device %s" % pingJob.hostname)


    def _checkManageInt(self, hostname):
        """check to see if manage interface is down before sending
        notifications about other interfaces"""
        if hostname.find(':') > -1:
            node = hostname.split(':')[0]
            if (self.goodDevices.has_key(node) and 
		self.goodDevices[node].pingStatus() > 0):
                return 1
        return 0


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
        #### sockets with bad addresses fail
        try:
            self.pingsocket.sendto(buf, (pingJob.address, 0))
        except SystemExit: raise
        except:
            pingJob.rtt = -1
            pingJob.message = "%s error sending to socket" % pingJob.address
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
            self.log.debug("received ip = %s id = %s" % (sourceip,icmppkt.id))
            if (icmppkt.id == self.procId and 
                self.jobqueue.has_key(sourceip)):
                pingJob = self.jobqueue[sourceip]
                pingJob.rtt = time.time() - pingJob.start
                pingJob.message = "%s is now reachable" % pingJob.hostname
                del self.jobqueue[sourceip]
                self.reportPingJob(pingJob)
            else:
                self.log.debug("got unexpected packet from %s" % sourceip)


    def checkTimeouts(self):
        """check to see if pingJobs in jobqueue have timed out"""
        joblist = self.jobqueue.values()
        for pingJob in joblist:
            if time.time() - pingJob.start > self.timeout:
                if pingJob.sent >= self.pingtries:
                    pingJob.rtt = -1
                    pingJob.message = "%s is unreachable" % pingJob.hostname 
                    del self.jobqueue[pingJob.address]
                    self.reportPingJob(pingJob)
                    self.sendPackets(1)
                else:
                    self.sendPacket(pingJob)


    def eventLoop(self, devices):
        startLoop = time.time()
        self.log.info("starting ping cycle %s" % (time.asctime()))
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
        self.log.info("ping cycle complete %s" % (time.asctime()))
        runtime = time.time() - startLoop
        self.log.info("pinged %d devices in %3.2f seconds" % 
                    (len(devices), runtime))
        return runtime
    

    def mainLoop(self):
        # for the first run, quit on failure
        if self.options.cycle:
            while 1:
                try:
                    self.getConfig()
                    runtime = self.eventLoop(self.goodDevices)
                    if runtime < self.cycleInterval:
                        time.sleep(self.cycleInterval - runtime)
                except SystemExit: raise
                except:
                    self.log.exception("unknown exception in main loop")
        else:
            self.getConfig()
            self.eventLoop(self.goodDevices)


    def _sendEvent(self, pingJob, nosev=0):
        """send an event to NcoProduct
        if nosev is true then don't use severity in Identifier"""
        url = basicAuthUrl(self.username, self.password, self.ncoserver)
        server = xmlrpclib.Server(url)
        event = {}
        node = pingJob.hostname.split(':')[0] #take out interface
        event['device'] = node
        event['summary'] = pingJob.message
        event['class'] = self.ncoClass
        event['agent'] = self.ncoAgent
        event['severity'] = pingJob.severity
        #event['Type'] = pingJob.type
        event['eventGroup'] = self.ncoAlertGroup
        event['ipAddress'] = pingJob.address
        event['manager'] = os.uname()[1]
        event['ownerUID'] = 65534
        event['ownerGID'] = 0
        try:
            server.sendEvent(event)
        except SystemExit: raise
        except:
            self.log.exception("netcool event notification failed"
                                "for server %s" % self.ncoserver)


    def buildOptions(self):
        StatusMonitor.buildOptions(self)
        self.parser.add_option("-z", "--zopeurl", action="store", 
                type="string", dest="zopeurl",
                help="XMLRPC url path for zope configuration server ")
        self.parser.add_option("-u", "--zopeusername", action="store", 
                type="string", dest="zopeusername",
                help="username for zope server")
        self.parser.add_option("-p", "--zopepassword", action="store", 
                type="string", dest="zopepassword",
                help="password for zope server")
        self.parser.add_option('-n', '--netcool',
                dest='netcool', default="",
                help="XMLRPC path to an NcoProduct instance")
        self.parser.add_option('-t', '--timeout',
                dest='timeout', default="1.0",
                help="time to wait before declaring ping dead")
        self.parser.add_option('-r', '--numbretries',
                dest='numbretries', default="2",
                help="retry times with in cycle before declaring device dead")
        self.parser.add_option('-w', '--cyclefailwarn',
                dest='cyclefailwarn', default="0",
                help="send a warning if device fails cyclefailwarn times")
        self.parser.add_option('-f', '--cyclefailcritical',
                dest='cyclefailcritical', default="0",
                help="send a critical if device fails cyclefailcritical times")
        self.parser.add_option('-H', '--chunksize',
                dest='chunksize', default="",
                help="number of packets to send before reading them back")
        self.parser.add_option('-g', '--configcycle',
                dest='configcycle', default=20,
                help="number of minutes between config reads")
        self.parser.add_option('--devicefile',
                dest='devicefile', default="",
                help="file with list of devices to ping")


class PingJob:
    '''Class representing a single
    target to be pinged'''

    def __init__(self, address, hostname, url, pingStatus):
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





if __name__=='__main__':
    if sys.platform == 'win32':
        time.time = time.clock
    pm = PingMonitor()
    pm.mainLoop()
