#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenperfsnmp

Gets snmp performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import socket
import time

from sets import Set

import Globals

from twisted.internet import reactor, defer

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenModel.PerformanceConf import performancePath

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol

BASE_URL = 'http://localhost:8080/zport/dmd'
DEFAULT_URL = BASE_URL + '/Monitors/StatusMonitors/localhost'
MAX_OIDS_PER_REQUEST = 200
MAX_SNMP_REQUESTS = 100

COMMON_EVENT_INFO = {
    'device':socket.getfqdn(),
    'component':'zenperfsnmp',
    }

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def rrdPath(branch):
    'compute where the RDD perf files should go'
    return performancePath(branch[1:] + '.rrd')

def firsts(lst):
    'the first element of every item in a sequence'
    return [item[0] for item in lst]

class Status:
    'keep track of the status of many parallel requests'
    _total = _success = _fail = 0
    _startTime = _stopTime = 0.0
    _deferred = None

    
    def start(self, count):
        'start the clock'
        self._total = count
        self._startTime = time.time()
        self._deferred = defer.Deferred()
        return self._deferred


    def record(self, successOrFailure):
        if successOrFailure:
            self.success()
        else:
            self.fail()

        
    def success(self, *unused):
        'record a successful result'
        self._success += 1
        self._checkFinished()


    def fail(self):
        'record a failed operation'
        self._fail += 1
        self._checkFinished()


    def _checkFinished(self):
        'determine the stopping point'
        if self.finished():
            self._stopTime = time.time()
            self._deferred.callback(self)


    def finished(self):
        'determine if we have finished everything'
        return self.outstanding() == 0


    def stats(self):
        'provide a summary of the effort'
        stopTime = self._stopTime
        if not self.finished():
            stopTime = time.time()
        return (self._total, self._success, self._fail,
                stopTime - self._startTime)


    def outstanding(self):
        'return the number of unfinished operations'
        return self._total - (self._success + self._fail)
    


class zenperfsnmp(ZenDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    startevt = {'eventClass':'/App/Start', 'summary': 'started', 'severity': 0}
    stopevt = {'eventClass':'/App/Stop', 'summary': 'stopped', 'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat'}
    for event in [startevt, stopevt, heartbeat]:
        event.update(COMMON_EVENT_INFO)

    # these names need to match the property values in StatusMonitorConf
    configCycleInterval = 20            # minutes
    snmpCycleInterval = 5*60            # seconds
    status = Status()

    def __init__(self):
        ZenDaemon.__init__(self)
        self.model = self.buildProxy(self.options.zopeurl)
        self.proxies = {}
        self.snmpPort = snmpprotocol.port()
        self.queryWorkList = Set()
        baseURL = '/'.join(self.options.zopeurl.rstrip('/').split('/')[:-2])
        if not self.options.zem:
            self.options.zem = baseURL + '/ZenEventManager'
        self.zem = self.buildProxy(self.options.zem)
        self.configLoaded = defer.Deferred()
        self.configLoaded.addCallbacks(self.readDevices, self.quit)
        self.unresponsiveDevices = Set()
        self.devicesRead = None

    def buildOptions(self):
        ZenDaemon.buildOptions(self)

        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server",
            default=DEFAULT_URL)
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("-p", "--zopepassword", dest="zopepassword")
        self.parser.add_option("--debug", dest="debug", action='store_true')
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance")

        
    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        url = basicAuthUrl(self.options.zopeusername,
                           self.options.zopepassword,
                           url)
        return AuthProxy(url)


    def sendEvent(self, event):
        'convenience function for pushing events to the Zope server'
        self.zem.callRemote('sendEvent', event).addErrback(self.log.debug)


    def setUnresponsiveDevices(self, deviceList):
        "remember all the unresponsive devices"
        self.log.debug('Unresponsive devices: %r' % deviceList)
        self.unresponsiveDevices = Set(firsts(deviceList))
        

    def cycle(self, seconds, callable):
        "callLater if we should be cycling"
        if self.options.debug:
            seconds /= 60
        reactor.callLater(seconds, callable)


    def startUpdateConfig(self):
        'Periodically ask the Zope server for basic configuration data.'
        lst = []
        deferred = self.model.callRemote('getDevices', True)
        deferred.addCallbacks(self.updateDeviceList, self.log.debug)
        lst.append(deferred)

        deferred = self.model.callRemote('propertyItems')
        deferred.addCallbacks(self.monitorConfigDefaults, self.log.error)
        lst.append(deferred)

        proxy = self.buildProxy(self.options.zem)
        deferred = proxy.callRemote('getWmiConnIssues')
        deferred.addCallbacks(self.setUnresponsiveDevices, self.log.error)
        lst.append(deferred)

        if not self.configLoaded.called:
            defer.DeferredList(lst).chainDeferred(self.configLoaded)

        self.cycle(self.configCycleInterval * 60, self.startUpdateConfig)


    def monitorConfigDefaults(self, items):
        'Unpack config defaults for this monitor'
        table = dict(items)
        for name in ('configCycleInterval', 'snmpCycleInterval'):
            if table.has_key(name):
                value = table[name]
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)

    def updateDeviceList(self, deviceList):
        'Update the config for devices devices'
        self.log.debug('Configured %d devices' % len(deviceList))

        if not deviceList: self.log.warn("no devices found")

        for snmpTargets in deviceList:
            self.updateDeviceConfig(snmpTargets)
            
        # stop collecting those no longer in the list
        deviceNames = Set(firsts(deviceList))
        doomed = Set(self.proxies.keys()) - deviceNames
        for name in doomed:
            self.log.debug('removing device %s' % name)
            del self.proxies[name]
            # we could delete the RRD files, too

    def updateDeviceConfig(self, snmpTargets):
        'Save the device configuration and create an SNMP proxy to talk to it'
        (deviceName, hostPort, snmpConfig, oidData) = snmpTargets
        if not oidData: return
        (ip, port)= hostPort
        (community, version, timeout, tries) = snmpConfig
        self.log.debug("received config for %s", deviceName)
        version = '2'
        if version.find('1') >= 0:
            version = '1'
        p = AgentProxy(ip=ip,
                       port=port,
                       community=community,
                       snmpVersion=version,
                       protocol=self.snmpPort.protocol,
                       allowCache=True)
        p.timeout = timeout
        p.tries = tries
        p.oidMap = {}
        for oid, path, dsType in oidData:
            oid = '.'+oid.lstrip('.')
            p.oidMap[oid] = path, dsType
        self.proxies[deviceName] = p


    def readDevices(self, unused=None):
        'Periodically fetch the performance values from all known devices'
        # limit the number of devices we query at once to avoid
        # a UDP packet storm
        if not self.status.finished():
            self.log.warning("There are still %d devices to query, "
                             "waiting for them to finish" %
                             self.status.outstanding())
        else:
            self.queryWorkList =  Set(self.proxies.keys())
            self.queryWorkList -= self.unresponsiveDevices
            self.status = Status()
            d = self.status.start(len(self.queryWorkList))
            d.addCallback(self.reportRate)
            for unused in range(MAX_SNMP_REQUESTS):
                if not self.queryWorkList: break
                self.startReadDevice(self.queryWorkList.pop())
        self.cycle(self.snmpCycleInterval, self.readDevices)


    def reportRate(self, *unused):
        'Finished reading all the devices, report stats and maybe stop'
        total, success, failed, runtime = self.status.stats()
        self.log.info("collected %d of %d devices in %.2f" %
                      (success, total, runtime))
        if not self.options.daemon and not self.options.cycle:
            reactor.stop()
        else:
            self.heartbeat['timeout'] = self.snmpCycleInterval * 3
            self.sendEvent(self.heartbeat)

    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        lst = []
        # ensure that the request will fit in a packet
        for part in chunk(proxy.oidMap.keys(), MAX_OIDS_PER_REQUEST):
            lst.append(proxy.get(part, proxy.timeout, proxy.tries))
        d = defer.DeferredList(lst, consumeErrors=True)
        d.addCallback(self.storeValues, deviceName)
        return d

    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'
        successCount = sum(firsts(updates))
        self.status.record(successCount == len(updates))
        self.log.debug('storeValues %r' % deviceName)
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # bad oid in request
        for success, update in updates:
            if success:
                for oid, value in update.items():
                    # performance monitoring should always get something back
                    if value == '':
                        self.log.warn('Suspect oid %s is bad' % oid)
                        del proxy.oidMap[oid]
                    else:
                        path, dsType = proxy.oidMap[oid]
                        self.storeRRD(path, dsType, value)
        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())


    def storeRRD(self, path, type, value):
        'store a value into an RRD file'
        import rrdtool
        filename = rrdPath(path)
        if not os.path.exists(filename):
            self.log.debug("create new rrd %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            dataSource = \
                'DS:%s:%s:%d:0:U' % ('ds0',type,3*self.snmpCycleInterval)
            rrdtool.create(filename,
                           "--step",  str(self.snmpCycleInterval),
                           dataSource,
                           'RRA:AVERAGE:0.5:1:600',
                           'RRA:AVERAGE:0.5:6:600',
                           'RRA:AVERAGE:0.5:24:600',
                           'RRA:AVERAGE:0.5:288:600',
                           'RRA:MAX:0.5:288:600')
        try:
            self.log.debug("update %s with %s", filename, value)
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            self.log.error('rrd error %s' % err)


    def quit(self, error):
        'stop the reactor if an error occured on the first config load'
        self.log.error(error)
        reactor.stop()


    def main(self):
        "Run forever, fetching and storing"

        self.sendEvent(self.startevt)
        
        zpf.startUpdateConfig()
        reactor.run()
        
        self.sendEvent(self.stopevt)

if __name__ == '__main__':
    zpf = zenperfsnmp()
    zpf.main()
