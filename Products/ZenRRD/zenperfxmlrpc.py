#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#   Copyright (c) 2006 Three Rings Design, Inc. All rights reserved.
#
#################################################################

__doc__='''zenperfxmlrpc

Gets xmlrpc performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import time
import logging
log = logging.getLogger("zen.zenperfxmlrpc")

from sets import Set

from twisted.internet import reactor, defer
from twisted.web.xmlrpc import Proxy

import Globals
from Products.ZenUtils.Chain import Chain
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_XmlRpc, Perf_XmlRpc

from RRDUtil import RRDUtil
from RRDDaemon import RRDDaemon, Threshold

from FileCleanup import FileCleanup

MAX_COMMANDS_PER_REQUEST = 40
MAX_XML_RPC_REQUESTS = 30

XMLRPC_UP = 0
XMLRPC_DOWN = 1


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
        self._checkFinished()           # count could be zero
        return self._deferred


    def record(self, successOrFailure):
        'single funtion to record success or failure'
        if successOrFailure:
            self.success()
        else:
            self.fail()

        
    def success(self, *unused):
        'record a successful result'
        self._success += 1
        self._checkFinished()


    def fail(self, *unused):
        'record a failed operation'
        self._fail += 1
        self._checkFinished()


    def _checkFinished(self):
        'determine the stopping point'
        if self.finished():
            self._stopTime = time.time()
            if not self._deferred.called:
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


    def moreWork(self, count):
        self._total += count


class XmlRpcStatus:
    "track and report XMLRPC status failures"

    xmlRpcStatusEvent = {'eventClass': Status_XmlRpc,
                       'component': 'xmlrpc',
                       'eventGroup': 'XmlRpcTest'}

    def __init__(self, xmlRpcState):
        # if the number of Event.Error severity events on this device is
        # greater than 0, than we consider the XMLRPC server down on this 
        # device
        if xmlRpcState > 0:
            self.xmlRpcState = XMLRPC_DOWN
        else:
            self.xmlRpcState = XMLRPC_UP
        self.proxyMap = {}


    def updateStatus(self, deviceName, success, eventCb):
        'Send events on XMLRPC failures'
        if success:
            if self.xmlRpcState == XMLRPC_DOWN:
                summary='XMLRPC server up on device ' + deviceName
                eventCb(self.xmlRpcStatusEvent,
                        device=deviceName, summary=summary,
                        severity=Event.Clear)
                log.info(summary)
            self.xmlRpcState = XMLRPC_UP
        else:
            if self.xmlRpcState == XMLRPC_UP:
                summary='XMLRPC server down on device ' + deviceName
                eventCb(self.xmlRpcStatusEvent,
                        device=deviceName, summary=summary,
                        severity=Event.Error)
                log.warn(summary)
            self.xmlRpcState = XMLRPC_DOWN


class XmlRpcData:
    def __init__(self, name, methodName, methodParameters, points):
        self.name = name
        self.methodName = methodName
        self.methodParameters = methodParameters
        self.points = []
        for point in points:
            thresholdObjs = [Threshold(*t) for t in point[-1]]
            self.points.append(list(point[:-1]) + [thresholdObjs])

class zenperfxmlrpc(RRDDaemon):
    "Periodically query all devices for XMLRPC values to archive in RRD files"

    initialServices = RRDDaemon.initialServices + ['XmlRPCConfig']

    # these names need to match the property values in StatusMonitorConf
    maxRrdFileAge = 30 * (24*60*60)     # seconds
    status = Status()

    xmlrpcCycleInterval = 1*60            # seconds
    heartBeatTimeout = xmlrpcCycleInterval*3

    properties = RRDDaemon.properties + ('xmlrpcCycleInterval',)

    def __init__(self):
        RRDDaemon.__init__(self, 'zenperfxmlrpc')
        self.devices = {}
        self.queryWorkList = Set()
        self.unresponsiveDevices = Set()
        self.cycleComplete = False
        self.methodsRequested = 0
        perfRoot = performancePath('')
        if not os.path.exists(perfRoot):
            os.makedirs(perfRoot)
        self.fileCleanup = FileCleanup(perfRoot, '.*\\.rrd$')
        self.fileCleanup.process = self.cleanup
        self.fileCleanup.start()

    def sendThresholdEvent(self, **kw):
        "Send the right event class for threshhold events"
        '''TODO /Perf/Snmp does not load as a filter in the GUI either. 
           Need to ask edahl about this.'''
        kw.setdefault('eventClass', Perf_XmlRpc)
        RRDDaemon.sendThresholdEvent(self, **kw)

    def setPropertyItems(self, items):
        RRDDaemon.setPropertyItems(self, items)
        self.heartBeatTimeout = self.xmlrpcCycleInterval*3

    def cleanup(self, fullPath):
        self.log.warning("Deleting old RRD file: %s", fullPath)
        try:
            os.unlink(fullPath)
        except OSError:
            self.log.error("Unable to delete old RRD file: %s", fullPath)

    def maybeQuit(self):
        "Stop if all performance has been fetched, and we aren't cycling"
        if self.cycleComplete and \
           not self.options.daemon and \
           not self.options.cycle:
            reactor.stop()


    def startUpdateConfig(self, driver):
        'Periodically ask the Zope server for basic configuration data.'

        driveLater(self.configCycleInterval * 60, self.startUpdateConfig)
        
        yield self.model().callRemote('getXmlRpcDevices', self.options.device)
        try:
            self.updateDeviceList(driver.next())
        except Exception, ex:
            self.log.exception(ex)
            raise

        yield self.model().callRemote('propertyItems')
        self.setPropertyItems(driver.next())
        
        yield self.model().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.rrd = RRDUtil(createCommand, self.xmlrpcCycleInterval)


    def updateDeviceList(self, deviceList):
        'Update the config for devices'
        if self.options.device:
            self.log.debug('Gathering xmlrpc performance data for %s ' %
                           self.options.device)

        if not deviceList:
            self.log.warn("no devices found, keeping existing list")
            return

        self.log.debug('Configured %d devices' % len(deviceList))

        for xmlrpcTargets in deviceList:
            self.updateDeviceConfig(xmlrpcTargets)
            
        # stop collecting those no longer in the list
        deviceNames = Set([d[0] for d in deviceList])
        doomed = Set(self.devices.keys()) - deviceNames
        for deviceName in doomed:
            self.log.debug('removing device %s' % deviceName)
            del self.devices[deviceName]
            # we could delete the RRD files, too


    def insertBasicAuth(self, url, username, password):
        import urlparse
        parsed = list(urlparse.urlsplit(url))
        parsed.insert(1, "%s:%s@%s" % (username, password, parsed[1]))
        parsed.pop(2)
        return urlparse.urlunsplit(parsed)


    def updateProxy(self, url, username, password, deviceStatus):
        "create or update proxy"
        if username and password:
            # if supplied a username and password we need to insert these
            # into the url key in the proxyMap so that URLs using
            # different credentials will get different proxies
            url_key = self.insertBasicAuth(url, username, password)
        else:
            url_key = url
        p = deviceStatus.proxyMap.get(url_key, None)
        if not p:
            p = Proxy(url, user=username, password=password)
            p.methodMap = {}
        return p, url_key

    def remote_deleteDevice(self, doomed):
        self.log.debug("Async delete device %s" % doomed)
        if doomed in self.devices:
             del self.devices[doomed]

    def remote_updateDeviceConfig(self, cfg):
        self.log.debug("Asynch update of config")
        self.updateDeviceConfig(cfg)


    def updateDeviceConfig(self, xmlRpcTargets):
        'Save the device configuration and create an XMLRPC proxy to talk to it'

        deviceName, xmlRpcState, xmlRpcData = xmlRpcTargets
        if not xmlRpcData: return
        self.log.debug("received config for %s", deviceName)

        deviceStatus = self.devices.get(deviceName, None)
        if not deviceStatus:
            deviceStatus = XmlRpcStatus(xmlRpcState)
            self.devices[deviceName] = deviceStatus

        for dsdef in xmlRpcData:
            (name, url, creds, methodName, methodParameters, points) = dsdef
            username, password = creds
            url = url.strip()
            username = username.strip()
            methodName = methodName.strip()
            p, url_key = self.updateProxy(url, username, password, deviceStatus)
            p.methodMap[methodName] = XmlRpcData(name,
                                                 methodName, methodParameters,
                                                 points)
            deviceStatus.proxyMap[url_key] = p


    def scanCycle(self, *unused):
        self.log.debug("getting device ping issues")
        d = self.getDevicePingIssues()
        d.addBoth(self.setUnresponsiveDevices)
        reactor.callLater(self.xmlrpcCycleInterval, self.scanCycle)


    def setUnresponsiveDevices(self, arg):
        "remember all the unresponsive devices"
        if isinstance(arg, list):
            deviceList = arg
            self.log.debug('Unresponsive devices: %r' % deviceList)
            self.unresponsiveDevices = Set(firsts(deviceList))
        else:
            self.log.error(arg)
        self.readDevices()

        
    def readDevices(self, unused=None):
        'Periodically fetch xmlrpc values from all known devices'
        
        if not self.status.finished():
            _, _, _, age = self.status.stats()
            if age < self.configCycleInterval * 2:
                self.log.warning("There are still %d devices to query, "
                                 "waiting for them to finish" %
                                 self.status.outstanding())
                return
            self.log.warning("Device status is not clearing.  Restarting.")

        self.queryWorkList = Set(self.devices.keys())
        self.queryWorkList -= self.unresponsiveDevices
        self.status = Status()
        d = self.status.start(len(self.queryWorkList))
        d.addCallback(self.reportRate)
        for unused in range(MAX_XML_RPC_REQUESTS):
            if not self.queryWorkList: break
            self.startReadDevice(self.queryWorkList.pop())


    def reportRate(self, *unused):
        'Finished reading all the devices, report stats and maybe stop'
        total, success, failed, runtime = self.status.stats()
        self.log.info("collected %d of %d devices in %.2f" %
                      (success, total, runtime))
        self.log.debug("Sent %d XMLRPC requests", self.methodsRequested)
        self.methodsRequested = 0
        self.heartbeat()


    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read all the xmlrpc URLS
        and all associated methods for a device'''
        deviceStatus = self.devices.get(deviceName, None)
        proxyMap = deviceStatus.proxyMap
        if proxyMap is None:
            return

        deferreds = []
        def iterAllMethods(proxy):
            for methodName in proxy.methodMap.keys():
                methodParameters = proxy.methodMap[methodName].methodParameters
                yield (proxy, methodName, methodParameters)

        def proxyValue(value, methodName):
            return (methodName, value)

        def getLater(parameters):
            proxy = parameters[0]
            methodName = parameters[1]
            methodParameters = parameters[2]
            params = []
            if methodParameters:
                from Products.ZenModel.RRDDataSource import convertMethodParameter 
                for p in methodParameters:
                    # convert the parameter to the type supplied but the user
                    converted = convertMethodParameter(p[0], p[1])    
                    params.append(converted)
            d = proxy.callRemote(methodName, *params)
            d.addCallback(proxyValue, methodName)
            self.methodsRequested += 1
            return d

        for url in proxyMap.keys():
            chain = Chain(getLater, iterAllMethods(proxyMap[url]))
            d = chain.run()
            d.addCallback(self.storeValues, deviceName, url)
            deferreds.append(d)
        d = defer.DeferredList(deferreds, fireOnOneErrback=False)
        d.addCallback(self.checkStatus, deviceName)
        return d


    def badMethodName(self, deviceName, url, methodName):
        proxy = self.devices[deviceName].proxyMap.get(url, None)
        if proxy is None:
            return
        name = proxy.methodMap[methodName].name
        summary = 'Read error on [url: %s] [method: %s]' % (url, methodName)
        self.sendEvent(self.devices[deviceName].xmlRpcStatusEvent,
                       device=deviceName, summary=summary,
                       component=name,
                       severity=Event.Info)
        self.log.warn(summary)
        del proxy.methodMap[methodName]


    def checkStatus(self, successCounts, deviceName):
        success = False
        for result, count in successCounts:
          # if any url for this device returned any successful methodName
          # value then we consider the device up
          if count > 0:
            success = True
            break
        self.status.record(success)

        self.devices[deviceName].updateStatus(deviceName, success, self.sendEvent)
       

    def storeValues(self, updates, deviceName, url):
        'decode responses from devices and store the elements in RRD files'

        proxy = self.devices[deviceName].proxyMap.get(url, None)
        methodMap = proxy.methodMap
        if methodMap is None:
            return

        successCount = sum(firsts(updates))
        methods = []
        for success, update in updates:
            if success:
                methodName = update[0]
                value = update[1]
                # should always get something back
                if value == '':
                    self.badMethodName(deviceName, url, methodName)
                else:
                    self.storeRRD(deviceName, url, methodName, value)
                    methods.append(methodName)

        # remove any targets that didn't report
        for doomed in Set(methodMap.keys()) - Set(methods):
            self.badMethodName(deviceName, url, doomed)

        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())

        if successCount:
            successPercent = successCount * 100 / len(updates)
            if successPercent not in (0, 100):
                self.log.debug("Successful request ratio for %s is %2d%%",
                               deviceName,
                               successPercent)

        return successCount


    def storeRRD(self, deviceName, url, methodName, value):
        'store a value into an RRD file'
        xmlRpcData = self.devices[deviceName].proxyMap[url].methodMap[methodName]
        for count, parts in enumerate(xmlRpcData.points):
            (name, path, dataStorageType,
             rrdCreateCommand, (min, max), thresholds) = parts

            # Decode the response
            vtype = type(value)
            if vtype == type({}):
                # dictionary response
                v = value.get(name, None)
            elif hasattr(value, '__getitem__'):
                # list, tuple
                v = value[count]
            elif count == 0:
                # single return value
                v = value
            else:
                log.warning('Cannot decode value %r for name %s', value, name)
                continue
            v = self.rrd.save(path, v, dataStorageType,
                              rrdCreateCommand, min=min, max=max)
            for threshold in thresholds:
                # use url+methodName+name as eventKey
                threshold.check(deviceName,
                                xmlRpcData.name,
                                url+methodName+name,
                                v,
                                self.sendThresholdEvent)

    def connected(self):
        "Run forever, fetching and storing"
        d = drive(zpf.startUpdateConfig)
        d.addCallbacks(self.scanCycle, self.errorStop)


if __name__ == '__main__':
    zpf = zenperfxmlrpc()
    zpf.run()
