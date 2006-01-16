#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__=''' ZenSnmp

Check the availability of the SNMP agent on a list of devices

$Id: ZenSnmp.py,v 1.42 2004/04/21 15:50:58 edahl Exp $'''

__version__ = "$Revision: 1.42 $"[11:-2]

import socket
import os
import time
import sys
import xmlrpclib
import logging
import asyncore
import pysnmp
from pysnmp.compat.pysnmp2x import asn1, v1, v2c, asynrole
from random import randrange

import Globals

from Products.ZenUtils.Utils import parseconfig, basicAuthUrl
from StatusMonitor import StatusMonitor


class ZenSnmp(StatusMonitor):
    
    ncoClass = "/Status/Snmp"
    ncoAgent = "ZenSnmp"
    ncoAlertGroup = "SnmpTest"
    heartbeat = {'eventClass':'/Heartbeat', 'device':socket.getfqdn(),
                'component': 'zenmon/zensnmp'}

    def __init__(self):
        StatusMonitor.__init__(self)
        self.pingconfsrv = self.options.zopeurl
        self.username = self.options.zopeusername
        self.password = self.options.zopepassword
        self.ncoserver = self.options.netcool 
        self.timeout = 1.2
        self.numTries = 3
        self.chunkSize = 50
        self.cycleInterval = 60
        self.configCycleInterval = 20
        self.configTime = 0
        self.devices = []
        self.oids = ['.1.3.6.1.2.1.1.3.0',]
        self.reqId = 0
        self.pending = {}
        self.processed = []
        self.manager = asynrole.manager((self.report, None))
        self.ncoeventqueue = []


    def validConfig(self):
        """let getConfig know if we have a working config or not"""
        return self.devices


    def loadConfig(self):
        """get the config data from server"""
        if time.time()-self.configTime > self.configCycleInterval*60:
            self.log.info("reloading configuration")
            url = basicAuthUrl(self.username, self.password,self.pingconfsrv)
            server = xmlrpclib.Server(url)
            self.timeout = server.getSnmpTimeOut()
            self.numTries = server.getSnmpTries()
            self.chunkSize = server.getChunk()
            self.cycleInterval = server.getSnmpCycleInterval()
            self.configCycleInterval = server.getConfigCycleInterval() 
            self.maxFailures = server.getMaxFailures()
            devices = server.getSnmpDevices()
            self.prepDevices(devices)
            self.configTime = time.time()
            self.heartbeat['timeout'] = self.cycleInterval*3


    def prepDevices(self, devices):
        """resolve dns names and make StatusTest objects"""
        self.devices = []
        self.baddevices = []
        for device in devices:
            hostname, url, currentStatus, community, snmpPort = device
            # resolve hostnames to ipaddresses
            try:
                ip = self.forwardDnsLookup(hostname)
                stattest = StatusTest(ip, hostname, 
                                    url, community,
                                    currentStatus,
                                    self.numTries, snmpPort)

                if currentStatus >= self.maxFailures:
                    self.log.debug("add %s to bad devices ping list" % hostname)
                    self.baddevices.append(stattest)
                else:
                    self.log.debug("add %s to main ping list" % hostname)
                    self.devices.append(stattest)

            except socket.error: 
                message = "%s is unresolvable in dns" % hostname
                self.log.warn(message)
                try:
                    url = basicAuthUrl(self.username, self.password, url)
                    devsrv = xmlrpclib.Server(url)
                    devsrv.setSnmpStatus(-2)
                except SystemExit: raise
                except:
                    self.log.exception("problem sending dns failure event")

        if self.baddevices and not self.options.skipbad:
            self.processLoop(self.baddevices)

    
    def sendSnmp(self, dchunk):
        """send out snmp requests"""
        for device in dchunk:
            self.sendSnmpToDevice(device)


    def sendSnmpToDevice(self, device):
        """send a single snmp request"""
        if device.community:
            req = v1.GETREQUEST()
            encoded_oids = map(asn1.OBJECTID().encode, self.oids)
            myreq = req.encode(request_id=self.reqId,
                               community=device.community, 
                               encoded_oids=encoded_oids)
        
            self.manager.send(myreq, (device.address, device.snmpPort))
            device.timeout = time.time() + self.timeout
            self.pending[req['request_id']] = (device, req)
            self.reqId += 1


    def report(self, manager, data, (response, src), exception):
        """called when some data comes back"""
        #if responce:
        if exception[0]:
            self.log.warn('exception occurred')
            self.log.warn(exception)
        else:
            (rsp, rest) = v1.decode(response)
            rspid = rsp['request_id']
            if self.pending.has_key(rspid):
                (device, req) = self.pending[rspid]
            else:
                self.log.warn("reply from %s didn't match any request" 
                                    % src[0]) 
                return
            try:
                vals = map(lambda x: x[0](), map(asn1.decode, 
                                rsp['encoded_vals']))
                device.uptime = vals[0]
                self.log.debug("%s has uptime of %s" % 
                                (device.hostname, device.uptime))
            except pysnmp.compat.pysnmp2x.asn1.TypeError, msg:
                device.uptime = -99
                self.log.warn("%s responded but decode failed: %s" % 
                                    (device.hostname, msg))
            self.processed.append(device)
            del self.pending[rspid]
            if len(self.pending) == 0 and not self.cycleInterval:
                self.manager.close()


    def processTimeout(self, now):
        """look for get requests that have timed out"""
        for reqid, (device, req) in self.pending.items():
            if device.timeout < now:
                device.retries -= 1
                if device.retries > 0:
                    self.sendSnmpToDevice(device)
                else:
                    #snmp is down log error update zope
                    #and send to netcool if we have a server
                    del self.pending[reqid]
                    device.message = ("no snmp response from %s" 
                                        % device.hostname)
                    self.log.warn(device.message)
                    if device.currentStatus < 0:
                        device.currentStatus = 1
                    else:
                        device.currentStatus += 1
                    self.processed.append(device)
        if len(self.pending) == 0 and not self.cycleInterval:
            self.manager.close()


    def notify(self):
        """send out notificaitons to the server"""
        url = basicAuthUrl(self.username, self.password, self.pingconfsrv)
        server = xmlrpclib.Server(url)
        self.log.debug('begining notification process')
        messages = []
        for device in self.processed:
            self.log.debug('notify for %s' % device.hostname)
            if device.uptime > device.lastuptime or device.uptime == -99:
                # snmp is back up after being down
                if device.currentStatus != 0:
                    if device.currentStatus >= self.maxFailures:
                        self.devices.append(device)
                    device.currentStatus = 0
                    self.log.debug('reset status for %s' % device.hostname)
                    messages.append((device.url, str(device.uptime)))
                    device.updateup = randrange(1,10)
                    if self.ncoserver:
                        device.message = ("snmp agent up on device %s" 
                                                    % device.hostname)
                        device.severity = 0
                        device.type = 2
                        self.queueNcoEvent(device)
                #update uptime of device
                if (device.updateup == 1):
                    device.updateup = randrange(1,10)
                    self.log.debug('will send uptime for %s' % device.hostname)
                    messages.append((device.url, str(device.uptime)))
                else:
                    device.updateup -= 1
                device.lastuptime = device.uptime
               

            #device is down send event if less than maxFailures
            elif (device.currentStatus > 0):
                #and device.currentStatus < self.maxFailures):
                self.log.debug(
                    'snmp failed set status for %s to %d' 
                    % (device.hostname, device.currentStatus)) 
                messages.append((device.url, str(-1)))
                if self.ncoserver:
                    device.message = ("snmp agent down on device %s" 
                                                % device.hostname)
                    device.severity = 4
                    device.type = 1
                    self.queueNcoEvent(device)
        try:
            self.log.debug("sending data to server")
            server.updateSnmpDevices(messages)
        except SystemExit: raise
        except:
            self.log.exception("failed to send uptimes to zope")
        if self.ncoserver: self.sendEvents()
        self.log.debug('data sent to server') 
        self.processed = []


    def processLoop(self, devices):
        """send out snmp and look for timeouts"""
        lendev = len(devices)
        for i in range(0, lendev, self.chunkSize):
            dchunk = devices[i: i + self.chunkSize]
            self.sendSnmp(dchunk)
            while self.pending:
                try:
                    asyncore.poll(self.timeout+0.01)
                except SystemExit: raise
                except:
                    self.log.exception("Exception while polling devices")
                self.processTimeout(time.time())
            self.notify()
   

    def mainLoop(self):
        """main polling loop"""
        if self.options.cycle:
            while 1:
                try:
                    startLoop = time.time()
                    # get config if necessary if we fail
                    # continue with the old config information
                    self.getConfig()
                    self.log.info("starting test cycle %s" % (time.asctime()))
                    self.processLoop(self.devices)
                    self.log.info("test cycle complete %s" % (time.asctime()))
                    self.log.info("tested %d devices in %3.2f seconds" % 
                                (len(self.devices), (time.time() - startLoop)))
                    runTime = time.time()-startLoop
                    if runTime < self.cycleInterval:
                        time.sleep(self.cycleInterval - runTime)
                except SystemExit: raise
                except:
                    self.log.exception("Exception in mainLoop")

        else:
            self.getConfig()
            startTime = time.time()
            self.processLoop(self.devices)
            self.log.info("tested %d devices in %3.2f seconds" % 
                        (len(self.devices), (time.time() - startTime)))
 

    def queueNcoEvent(self, statusTest):
        """place an event in the queue to be sent to the NcoProduct Server"""
        event = {}
        event['device'] = statusTest.hostname
        event['component'] = "snmp"
        event['summary'] = statusTest.message
        event['eventClass'] = self.ncoClass
        event['agent'] = self.ncoAgent
        event['severity'] = statusTest.severity
        #event['Type'] = statusTest.type
        event['eventGroup'] = self.ncoAlertGroup
        event['ipAddress'] = statusTest.address
        event['manager'] = os.uname()[1]
        self.ncoeventqueue.append(event)


    def sendEvents(self):
            self.ncoeventqueue.append(self.heartbeat)
            url = basicAuthUrl(self.username, self.password, self.ncoserver)
            server = xmlrpclib.Server(url)
            try:
                server.sendEvents(self.ncoeventqueue)
            except Exception, e:
                self.log.exception("netcool snmp event notification failed")
            self.ncoeventqueue = []


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
                dest='netcool',
                default="",
                help="XMLRPC path to an NcoProduct instance")
        self.parser.add_option("--skipbad", action="store_true", 
                default=0, dest="skipbad",
                help="skip testing the devices over pingthreshold")



class StatusTest:
    """track the results of a status test"""
    def __init__(self, address, hostname, url, 
                    community, currentStatus,
                    retries, snmpPort=161):
        self.address = address 
        self.hostname = hostname
        self.url = url
        self.community = community
        self.currentStatus = currentStatus
        self.snmpPort = int(snmpPort)
        self.retries = retries
        self.timeout = 0
        self.sent = 0
        self.message = ""
        self.uptime = 0
        self.lastuptime = 0
        self.updateup = randrange(1,10)


if __name__=='__main__':
    # fix platform dependance on time.time
    if sys.platform == 'win32':
        time.time = time.clock
    pm = ZenSnmp()
    pm.mainLoop()
