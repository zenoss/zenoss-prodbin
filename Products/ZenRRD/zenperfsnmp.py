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

import Globals

from twisted.internet import reactor, defer

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol 

DEFAULT_URL = 'http://localhost:8080/zport/dmd/Monitors/Cricket/localhost'
SAMPLE_CYCLE_TIME = 5*60
CONFIG_CYCLE_TIME = 20*60
MAX_OIDS_PER_REQUEST = 200
MAX_SNMP_REQUESTS = 100

SAMPLE_CYCLE_TIME = 5

def chunk(lst, n):
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def rrdPath(branch):
    root = os.path.join(os.getenv('ZENHOME'), 'perf')
    r = os.path.join(root, branch[1:] + '.rrd')
    return r

def nameFromPath(branch):
    name = os.path.split(branch)[-1]
    name = ''.join(name.split(' '))
    name = '_'.join(name.split('-'))
    return name

class ZenPerformanceFetcher(ZenDaemon):

    def __init__(self):
        ZenDaemon.__init__(self)
        self.model = None
        self.proxies = {}
        self.snmpPort = snmpprotocol.port()
        self.queryWorkList = []


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
        self.parser.add_option("--debug", dest="debug", action='store_true')


    def startUpdateConfig(self):
        'Periodically ask the Zope server for the device list.'
        if not self.model:
            url = basicAuthUrl(self.options.zopeusername,
                               self.options.zopepassword,
                               self.options.zopeurl)
            self.model = AuthProxy(url)
        deferred = self.model.callRemote('cricketDeviceList', True)
        deferred.addCallbacks(self.updateConfig, self.reconnect)
        reactor.callLater(CONFIG_CYCLE_TIME, self.startUpdateConfig)


    def updateConfig(self, deviceList):
        '''Update the list of devices, and initiate a request
        to get the device configuration'''
        for device in deviceList:
            self.startDeviceConfig(device)
        # stop collecting those no longer in the list
        doomed = set(self.proxies.keys()) - set(deviceList)
        for device in doomed:
            del self.proxies[device]
            # we could delete the RRD files, too


    def startDeviceConfig(self, deviceUrl):
        'Kick off a request to get the configuration of a device'
        devUrl = basicAuthUrl(self.options.zopeusername,
                              self.options.zopepassword,
                              deviceUrl)
        proxy = AuthProxy(devUrl)
        d = proxy.callRemote('getSnmpOidTargets')
        d.addCallbacks(self.updateDeviceConfig, self.logError)


    def updateDeviceConfig(self, snmpTargets):
        'Save the device configuration and create an SNMP proxy to talk to it'
        deviceName, ip, port, community, oidData = snmpTargets
        p = AgentProxy(ip=ip, port=port,
                       community=community,
                       protocol=self.snmpPort.protocol,
                       allowCache=True)
        p.badOidMode = False
        p.oidMap = {}
        for oid, path, dsType in oidData:
            p.oidMap[oid] = path, dsType
        self.proxies[deviceName] = p


    def readDevices(self):
        'Periodically fetch the performance values from all known devices'
        # limit the number of devices we query at once to avoid
        # a UDP packet storm
        if self.queryWorkList:
            self.log.warning("There are still %d devices to query, "
                             "waiting for them to finish" %
                             len(self.queryWorkList))
        else:
            self.queryWorkList = self.proxies.keys()
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

if __name__ == '__main__':
    zpf = ZenPerformanceFetcher()
    zpf.startUpdateConfig()
    zpf.readDevices()
    reactor.run()
