
import Globals

from twisted.internet import reactor

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol 

import os
import random

SAMPLE_CYCLE_TIME = 5*60
CONFIG_CYCLE_TIME = 20*60
MAX_OIDS_PER_REQUEST = 200

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

    def buildOptions(self):
        ZenDaemon.buildOptions(self)

        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server ",
            default='http://localhost:8080/zport/dmd/Monitors/Cricket/localhost')
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("-p", "--zopepassword", dest="zopepassword")
        self.parser.add_option("--debug", dest="debug", action='store_true')

    def startUpdateConfig(self):
        if not self.model:
            url = basicAuthUrl(self.options.zopeusername,
                               self.options.zopepassword,
                               self.options.zopeurl)
            print url
            self.model = AuthProxy(url)
        deferred = self.model.callRemote('cricketDeviceList', True)
        deferred.addCallbacks(self.updateConfig, self.reconnect)
        reactor.callLater(CONFIG_CYCLE_TIME, self.startUpdateConfig)

    def updateConfig(self, deviceList):
        for device in deviceList:
            self.startDeviceConfig(device)
        # stop collecting those no longer in the list
        doomed = set(self.proxies.keys()) - set(deviceList)
        for device in doomed:
            del self.proxies[device]
            # we could delete the RRD files, too

    def startDeviceConfig(self, deviceUrl):
        devUrl = basicAuthUrl(self.options.zopeusername,
                              self.options.zopepassword,
                              deviceUrl)
        proxy = AuthProxy(devUrl)
        proxy.callRemote('getSnmpOidTargets').addCallbacks(self.updateDeviceConfig,
                                                           self.logError)

    def updateDeviceConfig(self, snmpTargets):
        deviceName, ip, port, community, oidData = snmpTargets
        p = AgentProxy(ip=ip, port=port,
                       community=community,
                       protocol=self.snmpPort.protocol,
                       allowCache=True)
        p.oidMap = dict([(oid, (path, type)) for oid, path, type in oidData])
        oldProxy = self.proxies.get(deviceName, None)
        self.proxies[deviceName] = p
        if oldProxy is None:
            # new device, fetch data right away
            self.startReadDevice(deviceName)

    def readDevices(self):
        # stagger the fetch of to avoid a UDP packet storm every read cycle  
        for deviceName in self.proxies.keys():
            randomWait = random.randrange(0, max(SAMPLE_CYCLE_TIME / 2, 1))
            reactor.callLater(randomWait, self.startReadDevice, deviceName)
        reactor.callLater(SAMPLE_CYCLE_TIME, self.readDevices)

    def startReadDevice(self, deviceName):
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        for part in chunk(proxy.oidMap.keys(), MAX_OIDS_PER_REQUEST):
            proxy.get(part).addCallbacks(self.storeValues, self.logError, (deviceName,))

    def storeValues(self, updates, deviceName):
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # oids start with '.' coming back from the client
        for oid, value in updates.items():
            path, type = proxy.oidMap[oid.strip('.')]
            self.storeRRD(path, type, value)
        print deviceName, '-'*20

    def storeRRD(self, path, type, value):
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
        self.model = None
        self.log.error('connection to Zope server dropped (reconnecting)')

if __name__ == '__main__':
    zpf = ZenPerformanceFetcher()
    zpf.startUpdateConfig()
    zpf.readDevices()
    reactor.run()
