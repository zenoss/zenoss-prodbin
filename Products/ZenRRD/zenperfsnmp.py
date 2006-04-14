#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''ZenPerformanceFetcher

Gets snmp performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import socket

import Globals

from twisted.internet import reactor, defer

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenEvents.SendEvent import SendEvent

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol

DEFAULT_URL = 'http://localhost:8080/zport/dmd/Monitors/Cricket/localhost'
EVENT_URL = 'http://localhost:8080/zport/dmd/ZenEventManager'
SAMPLE_CYCLE_TIME = 5*60
CONFIG_CYCLE_TIME = 20*60
MAX_OIDS_PER_REQUEST = 200
MAX_SNMP_REQUESTS = 100

COMMON_EVENT_INFO = {
    'device':socket.getfqdn(),
    'component':'zenperfsnmp'
    }

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def rrdPath(branch):
    'compute where the RDD perf files should go'
    root = os.path.join(os.getenv('ZENHOME'), 'perf')
    r = os.path.join(root, branch[1:] + '.rrd')
    return r

def nameFromPath(branch):
    'Pick an RRD data source name from the path name'
    name = os.path.split(branch)[-1]
    name = ''.join(name.split(' '))
    name = '_'.join(name.split('-'))
    return name

class ZenPerformanceFetcher(ZenDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    startevt = {'eventClass':'/App/Start', 'summary': 'started', 'severity': 0}
    stopevt = {'eventClass':'/App/Stop', 'summary': 'stopped', 'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat'}
    for event in [startevt, stopevt, heartbeat]:
        event.update(COMMON_EVENT_INFO)


    def __init__(self):
        ZenDaemon.__init__(self)
        self.model = None
        self.proxies = {}
        self.snmpPort = snmpprotocol.port()
        self.queryWorkList = []
        self.zem = SendEvent('PerformanceFetcher',
                             self.options.zopeusername,
                             self.options.zopepassword,
                             self.options.zem)
        self.deviceLoopStarted = False
        self.unresponsiveDevices = []


    def buildOptions(self):
        ZenDaemon.buildOptions(self)

        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server ",
            default=DEFAULT_URL)
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("-p", "--zopepassword", dest="zopepassword")
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance",
            default=EVENT_URL)
        self.parser.add_option("--debug", dest="debug", action='store_true')


    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        url = basicAuthUrl(self.options.zopeusername,
                           self.options.zopepassword,
                           url)
        return AuthProxy(url)


    def startFetchUnresponsiveDevices(self, devices):
        "start fetching the devices that are unresponsive"
        proxy = self.buildProxy(self.options.zem)
        d = proxy.callRemote('getWmiConnIssues')
        d.addCallbacks(self.setUnresponsiveDevices, self.logError)


    def setUnresponsiveDevices(self, deviceStatus):
        "remember all the unresponsive devices"
        self.unresponsiveDevices = [d[0] for d in deviceStatus]


    def startUpdateConfig(self):
        'Periodically ask the Zope server for the device list.'
        if not self.model:
            self.model = self.buildProxy(self.options.zopeurl)
        deferred = self.model.callRemote('cricketDeviceList', True)
        deferred.addCallbacks(self.updateConfig, self.reconnect)
        reactor.callLater(CONFIG_CYCLE_TIME, self.startUpdateConfig)


    def updateConfig(self, deviceList):
        '''Update the list of devices, and initiate a request
        to get the device configuration'''
        lst = []
        for device in deviceList:
            lst.append(self.startDeviceConfig(device))
        defer.DeferredList(lst, consumeErrors=1).addCallback(self.readDevices1)

        self.startFetchUnresponsiveDevices(deviceList)
            
        # stop collecting those no longer in the list
        doomed = set(self.proxies.keys()) - set(deviceList)
        for device in doomed:
            del self.proxies[device]
            # we could delete the RRD files, too


    def startDeviceConfig(self, deviceUrl):
        'Kick off a request to get the configuration of a device'
        proxy = self.buildProxy(deviceUrl)
        d = proxy.callRemote('getSnmpOidTargets')
        d.addCallbacks(self.updateDeviceConfig, self.logError)
        return d


    def updateDeviceConfig(self, snmpTargets):
        'Save the device configuration and create an SNMP proxy to talk to it'
        deviceName, ip, port, community, oidData = snmpTargets
        p = AgentProxy(ip=ip, port=port, community=community,
                       protocol=self.snmpPort.protocol, allowCache=True)
        p.badOidMode = False
        p.oidMap = {}
        for oid, path, dsType in oidData:
            p.oidMap[oid] = path, dsType
        self.proxies[deviceName] = p
        return snmpTargets

    def readDevices1(self, *ignored):
        "Start the read devices timer after we have collected device configs"
        if self.deviceLoopStarted: return
        self.deviceLoopStarted = True
        self.readDevices()

    def readDevices(self):
        'Periodically fetch the performance values from all known devices'
        # limit the number of devices we query at once to avoid
        # a UDP packet storm
        if self.queryWorkList:
            self.log.warning("There are still %d devices to query, "
                             "waiting for them to finish" %
                             len(self.queryWorkList))
        else:
            self.queryWorkList =  set(self.proxies.keys())
            self.queryWorkList -= set(self.unresponsiveDevices)
            for i in range(MAX_SNMP_REQUESTS):
                if not self.queryWorkList: break
                self.startReadDevice(self.queryWorkList.pop())
        reactor.callLater(SAMPLE_CYCLE_TIME, self.readDevices)


    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        lst = []
        if proxy.badOidMode:
            # creep through oids to find the bad oid
            for oid in proxy.oidMap.keys():
                d = proxy.get([oid])
                d.addCallback(self.noticeBadOid, deviceName, oid)
                lst.append(d)
        else:
            # ensure that the request will fit in a packet
            for part in chunk(proxy.oidMap.keys(), MAX_OIDS_PER_REQUEST):
                lst.append(proxy.get(part))
        deferred = defer.DeferredList(lst, consumeErrors=1)
        deferred.addCallbacks(self.storeValues,
                              self.finishDevices,
                              (deviceName,))

    def noticeBadOid(self, result, deviceName, oid):
        'Remove Oids that return empty responses'
        proxy = self.proxies.get(deviceName, None)
        if proxy is None: return
        if not result:
            self.logError('Bad oid %s found for device %s' % (oid, deviceName))
            del proxy.oidMap[oid]
            return (False, result)
        return (True, result)


    def finishDevices(self, error=None):
        'work down the list of devices'
        if error:
            self.logError(error)
        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())


    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # bad oid in request
        if proxy.badOidMode:
            # bad scan complete, clear the flag
            proxy.badOidMode = False
            return
        for success, update in updates:
            if success:
                if not update:
                    proxy.badOidMode = True
                for oid, value in update.items():
                    # oids start with '.' coming back from the client
                    path, dsType = proxy.oidMap[oid.strip('.')]
                    self.storeRRD(path, dsType, value)
        if proxy.badOidMode:
            self.queryWorkList.append(deviceName)
        self.finishDevices()


    def storeRRD(self, path, type, value):
        'store a value into an RRD file'
        import rrdtool
        filename = rrdPath(path)
        if not os.path.exists(filename):
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            dataSource = 'DS:%s:%s:%d:0:U' % (nameFromPath(path),
                                              type,
                                              CONFIG_CYCLE_TIME)
            rrdtool.create(filename,
                           dataSource,
                           'RRA:AVERAGE:0.5:1:600',
                           'RRA:AVERAGE:0.5:6:600',
                           'RRA:AVERAGE:0.5:24:600',
                           'RRA:AVERAGE:0.5:288:600',
                           'RRA:MAX:0.5:288:600')
        try:
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            self.log.error('rrd error %s' % err)

    def logError(self, error):
        self.log.error(error)

    def reconnect(self, error):
        'Errback for handling communications errors with the Zope server'
        self.model = None
        self.log.error('connection to Zope server dropped (%s), '
                       'reconnecting' % error)

    def beat(self):
        self.zem.server.sendEvent(self.heartbeat)
        reactor.callLater(SAMPLE_CYCLE_TIME, self.beat)

    def main(self):
        "Run forever, fetching and storing"
        self.heartbeat['timeout'] = SAMPLE_CYCLE_TIME * 3
        self.zem.server.sendEvent(self.startevt)
        
        zpf.startUpdateConfig()
        self.beat()
        reactor.run()
        
        self.zem.server.sendEvent(self.stopevt)

if __name__ == '__main__':
    zpf = ZenPerformanceFetcher()
    zpf.main()
