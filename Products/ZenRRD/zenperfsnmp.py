#! /usr/bin/env python 
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

__doc__="""zenperfsnmp

Gets SNMP performance data and stores it in RRD files.

"""

import os
import time
import logging
log = logging.getLogger("zen.zenperfsnmp")

from sets import Set
import cPickle

from twisted.internet import reactor, defer, error
from twisted.python import failure

import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Chain import Chain
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses \
     import Perf_Snmp, Status_Snmp, Status_Perf
from Products.ZenEvents.ZenEventClasses import Critical, Clear

from Products.ZenRRD.RRDUtil import RRDUtil
from SnmpDaemon import SnmpDaemon

from FileCleanup import FileCleanup

# PerformanceConfig import needed to get pb to work
from Products.ZenHub.services.PerformanceConfig import PerformanceConfig
unused(PerformanceConfig)

MAX_OIDS_PER_REQUEST = 40
MAX_SNMP_REQUESTS = 20
DEVICE_LOAD_CHUNK_SIZE = 2

def makeDirs(dir):
    """
    Wrapper around makedirs that sanity checks before running
    """
    if os.path.exists(dir):
        return

    try:
        os.makedirs(dir, 0750)
    except Exception, ex:
        log.critical( "Unable to create directories for %s because %s" % ( dir, ex ) )


def read(fname):
    """
    Wrapper around the standard function to open a file and read its contents
    """
    if os.path.exists(fname):
        fp = file(fname, 'rb')
        try:
            return fp.read()
        finally:
            fp.close()
    return ''


def write(fname, data):
    """
    Wrapper around the standard function to open a file and write data
    """
    makeDirs(os.path.dirname(fname))

    try:
        fp = open(fname, 'wb')
        try:
            fp.write(data)
        finally:
            fp.close()

    except Exception, ex:
        log.critical( "Unable to write data to %s because %s" % ( fname, ex ) )


def unlink(fname):
    """
    Wrapper around the standard function to delete a file
    """
    if os.path.exists(fname):
        os.unlink(fname)

def chunk(lst, n):
    """
    Break lst into n-sized chunks
    """
    return [lst[i:i+n] for i in range(0, len(lst), n)]

try:
    sorted = sorted                     # added in python 2.4
except NameError:
    def sorted(lst, *args, **kw):
        """
        Keep things sane in a pre-python 2.4 environment
        """
        lst.sort(*args, **kw)
        return lst

def firsts(lst):
    """
    The first element of every item in a sequence
    """
    return [item[0] for item in lst]

def checkException(alog, function, *args, **kw):
    """
    Execute the function with arguments and keywords.
    If there is an exception, log it using the given
    logging function 'alog'.
    """
    try:
        return function(*args, **kw)
    except Exception, ex:
        alog.exception(ex)
        raise ex



from twisted.spread import pb
class SnmpConfig(pb.Copyable, pb.RemoteCopy):
    """
    A class to transfer the SNMP collection data to zenperfsnmp
    """

    lastChangeTime = 0.
    device = ''
    connInfo = None
    thresholds = []
    oids = []

pb.setUnjellyableForClass(SnmpConfig, SnmpConfig)

        
class Status:
    """
    Keep track of the status of many parallel requests
    """
    _success = _fail = 0
    _startTime = _stopTime = 0.0
    _deferred = None

    def __init__(self):
        """
        Initializer
        """
        self._allDevices = Set()
        self._reported = Set()
    
    def start(self, devices):
        """
        Record our start time, and return a deferred for our devices
        """
        self._allDevices = Set(devices)
        self._reported = Set()
        self._startTime = time.time()
        self._deferred = defer.Deferred()
        self._checkFinished()           # count could be zero
        return self._deferred


    def record(self, name, successOrFailure):
        """
        Record success or failure
        """
        if name in self._reported:
            log.error("Device %s is reporting more than once", name)
            return
        self._reported.add(name)
        if successOrFailure:
            self.success()
        else:
            self.fail()

        
    def success(self, *unused):
        """
        Record a successful result
        """
        self._success += 1
        self._checkFinished()


    def fail(self, *unused):
        """
        Record a failed operation
        """
        self._fail += 1
        self._checkFinished()


    def _checkFinished(self):
        """
        Determine the stopping point and log our current stats
        """
        if self.finished():
            self._stopTime = time.time()
            if not self._deferred.called:
                self._deferred.callback(self)
        log.info("total=%d good=%d bad=%d time=%f", * self.stats())


    def finished(self):
        """
        Determine if we have finished everything
        """
        return self.outstanding() <= 0


    def stats(self):
        """
        Return a tuple with:
         * number of devices
         * number of successful operations
         * number of failed operations
         * amount of time since our last start() operation
        """
        age = self._stopTime - self._startTime
        if not self._startTime:
            age = 0.0
        elif not self.finished():
            age = time.time() - self._startTime
        return (len(self._allDevices), self._success, self._fail, age)


    def outstanding(self):
        """
        Return the number of unfinished operations
        """
        return len(self.outstandingNames())

    def outstandingNames(self):
        """
        Return the set of unfinished operations
        """
        return self._allDevices - self._reported


class SnmpStatus:
    """
    Track and report SNMP status failures
    """

    snmpStatusEvent = {'eventClass': Status_Snmp,
                       'component': 'snmp',
                       'eventGroup': 'SnmpTest'}

    
    def __init__(self, snmpState):
        """
        Initializer
        """
        self.count = snmpState


    def updateStatus(self, deviceName, success, eventCb):
        """
        Send up/down events based on SNMP results
        """
        if success:
            if self.count > 0:
                summary='SNMP agent up'
                eventCb(self.snmpStatusEvent, 
                        device=deviceName, summary=summary,
                        severity=Event.Clear)
                log.info(summary)
            self.count = 0
        else:
            summary='SNMP agent down'
            eventCb(self.snmpStatusEvent,
                    device=deviceName, summary=summary,
                    severity=Event.Error)
            log.warn(summary)
            self.count += 1



class OidData:
    def update(self, name, path, dataStorageType, rrdCreateCommand, minmax):
        """
        Container for these paramaters
        """
        self.name = name
        self.path = path
        self.dataStorageType = dataStorageType
        self.rrdCreateCommand = rrdCreateCommand
        self.minmax = minmax

class zenperfsnmp(SnmpDaemon):
    """
    Periodically query all devices for SNMP values to archive in RRD files
    """
    
    # these names need to match the property values in PerformanceMonitorConf
    maxRrdFileAge = 30 * (24*60*60)     # seconds
    perfsnmpConfigInterval = 20*60
    perfsnmpCycleInterval = 5*60
    properties = SnmpDaemon.properties + ('perfsnmpCycleInterval',)
    initialServices = SnmpDaemon.initialServices + ['SnmpPerfConfig']

    def __init__(self, noopts=0):
        """
        Create any base performance directories (if necessary),
        load cached configuration data and clean up any old RRD files
        (if specified by --checkAgingFiles)
        """
        SnmpDaemon.__init__(self, 'zenperfsnmp', noopts)
        self.status = None
        self.proxies = {}
        self.queryWorkList = Set()
        self.unresponsiveDevices = Set()
        self.snmpOidsRequested = 0

        self.log.info( "Initializing daemon..." )

        perfRoot = performancePath('')
        makeDirs(perfRoot)

        if self.options.cacheconfigs:
            self.loadConfigs()

        self.oldFiles = Set()

        # report on files older than a day
        if self.options.checkagingfiles:
            self.oldCheck = FileCleanup(perfRoot, '.*\\.rrd$',
                                        24 * 60 * 60,
                                        frequency=60)
            self.oldCheck.process = self.reportOldFile
            self.oldCheck.start()

        # remove files older than maxRrdFileAge
        self.fileCleanup = FileCleanup(perfRoot, '.*\\.rrd$',
                                       self.maxRrdFileAge,
                                       frequency=90*60)
        self.fileCleanup.process = self.cleanup
        self.fileCleanup.start()


    def pickleName(self, id):
        """
        Return the path to the pickle file for a device
        """
        return performancePath('Devices/%s/%s-config.pickle' % (id, self.options.monitor))



    def loadConfigs(self):
        """
        Read cached configuration values from pickle files at startup.

        NB: We cache in pickles to get a full collect cycle, because
            loading the initial config can take several minutes.
        """
        self.log.info( "Gathering cached configuration information" )

        base = performancePath('Devices')
        makeDirs(base)
        root, ds, fs = os.walk(base).next()
        for d in ds:
            pickle_name= self.pickleName(d)
            config = read( pickle_name )
            if config:
                try:
                    self.log.debug( "Reading cached config info from pickle file %s" % pickle_name )
                    data= cPickle.loads(config)
                    self.updateDeviceConfig( data )

                except Exception, ex:
                    self.log.warn( "Received %s while loading cached configs in %s -- ignoring" % (ex, pickle_name ) )
                    try:
                        os.unlink( pickle_name )
                    except Exception, ex:
                        self.log.warn( "Unable to delete corrupted pickle file %s because %s" % ( pickle_name, ex ) )



    def cleanup(self, fullPath):
        """
        Delete an old RRD file
        """
        self.log.warning("Deleting old RRD file: %s", fullPath)
        os.unlink(fullPath)
        self.oldFiles.discard(fullPath)


    def reportOldFile(self, fullPath):
        """
        Add an RRD file to the list of files to be removed
        """
        self.oldFiles.add(fullPath)


    def maybeQuit(self):
        """
        Stop if all performance has been fetched, and we aren't cycling
        """
        if not self.options.daemon and \
           not self.options.cycle:
            reactor.callLater(0, reactor.stop)


    def remote_updateDeviceList(self, devices):
        """
        Gather the list of devices from zenhub, update all devices config
        in the list of devices, and remove any devices that we know about,
        but zenhub doesn't know about.

        NB: This is callable from within zenhub.
        """
        SnmpDaemon.remote_updateDeviceList(self, devices)
        # NB: Anything not explicitly sent by zenhub should be deleted
        survivors = []
        doomed = Set(self.proxies.keys())
        for device, lastChange in devices:
            doomed.discard(device)
            proxy = self.proxies.get(device)
            if not proxy or proxy.lastChange < lastChange:
                survivors.append(device)

        log.info("Deleting %s", doomed)
        for d in doomed:
            del self.proxies[d]

        if survivors:
            log.info("Fetching configs: %s", survivors)
            d = self.model().callRemote('getDevices', survivors)
            d.addCallback(self.updateDeviceList, survivors)
            d.addErrback(self.error)



    def startUpdateConfig(self, driver):
        """
        Periodically ask the Zope server for basic configuration data.
        """

        now = time.time()
        
        log.info("Fetching property items...")
        yield self.model().callRemote('propertyItems')
        self.setPropertyItems(driver.next())

        driveLater(self.configCycleInterval * 60, self.startUpdateConfig)

        log.info("Getting threshold classes...")
        yield self.model().callRemote('getThresholdClasses')
        self.remote_updateThresholdClasses(driver.next())
        
        log.info("Checking for outdated configs...")
        current = [(k, v.lastChange) for k, v in self.proxies.items()]
        yield self.model().callRemote('getDeviceUpdates', current)

        devices = driver.next()
        if self.options.device:
            devices = [self.options.device]

        log.info("Fetching configs for %s", repr(devices)[0:800]+'...')
        yield self.model().callRemote('getDevices', devices)
        updatedDevices = driver.next()

        log.info("Fetching default RRDCreateCommand...")
        yield self.model().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.rrd = RRDUtil(createCommand, self.perfsnmpCycleInterval)

        log.info( "Getting collector thresholds..." )
        yield self.model().callRemote('getCollectorThresholds')
        self.rrdStats.config(self.options.monitor, self.name, driver.next(),
                             createCommand)
                
        log.info("Fetching SNMP status...")
        yield self.model().callRemote('getSnmpStatus', self.options.device)
        self.updateSnmpStatus(driver.next())

        # Kick off the device load
        log.info("Initiating incremental device load")
        d = self.updateDeviceList(updatedDevices, devices)
        def report(result):
            """
            Twisted deferred errBack to check for errors
            """
            if result:
                log.error("Error loading devices: %s", result)
        d.addBoth(report)
        self.sendEvents(self.rrdStats.gauge('configTime',
                                            self.configCycleInterval * 60,
                                            time.time() - now))


    def updateDeviceList(self, responses, requested):
        """
        Update the config for devices
        """

        def fetchDevices(driver):
            """
            An iterable to go over the list of devices
            """
            deviceNames = Set()
            length = len(responses)
            log.debug("Fetching configs for %d devices", length)
            for devices in chunk(responses, DEVICE_LOAD_CHUNK_SIZE):
                log.debug("Fetching config for %s", devices)
                yield self.model().callRemote('getDeviceConfigs', devices)
                try:
                    for response in driver.next():
                       self.updateDeviceConfig(response)
                except Exception, ex:
                    log.warning("Error loading config for devices %s" % devices)
                for d in devices:
                    deviceNames.add(d)
            log.debug("Finished fetching configs for %d devices", length)

            # stop collecting those no longer in the list
            doomed = Set(requested) - deviceNames
            if self.options.device:
                self.log.debug('Gathering performance data for %s ' %
                               self.options.device)
                doomed = Set(self.proxies.keys())
                doomed.discard(self.options.device)
            for name in doomed:
                self.log.info('Removing device %s' % name)
                if name in self.proxies:
                    del self.proxies[name]

                # Just in case, delete any pickle files that might exist
                config = self.pickleName(name)
                unlink(config)
                # we could delete the RRD files, too

            ips = Set()
            for name, proxy in self.proxies.items():
                if proxy.snmpConnInfo.manageIp in ips:
                    log.warning("Warning: device %s has a duplicate address %s",
                                name, proxy.snmpConnInfo.manageIp)
                ips.add(proxy.snmpConnInfo.manageIp)
            self.log.info('Configured %d of %d devices',
                          len(deviceNames), len(self.proxies))
            yield defer.succeed(None)
        return drive(fetchDevices)



    def updateAgentProxy(self, deviceName, snmpConnInfo):
        """
        Create or update proxy

        @parameter deviceName: device name known by zenhub
        @type deviceName: string
        @parameter snmpConnInfo: object information passed from zenhub
        @type snmpConnInfo: class SnmpConnInfo from Products/ZenHub/services/PerformanceConfig.py
        @return: connection information from the proxy
        @rtype: SnmpConnInfo class
        """
        p = self.proxies.get(deviceName, None)
        if not p:
            p = snmpConnInfo.createSession(protocol=self.snmpPort.protocol,
                                           allowCache=True)
            p.oidMap = {}
            p.snmpStatus = SnmpStatus(0)
            p.singleOidMode = False
            p.lastChange = 0

        if p.snmpConnInfo != snmpConnInfo:
            t = snmpConnInfo.createSession(protocol=self.snmpPort.protocol,
                                           allowCache=True)
            t.oidMap = p.oidMap
            t.snmpStatus = p.snmpStatus
            t.singleOidMode = p.singleOidMode
            t.lastChange = p.lastChange
            p = t

        return p



    def updateSnmpStatus(self, status):
        """
        Update the SNMP failure counts from Status database
        """
        countMap = dict(status)
        for name, proxy in self.proxies.items():
            proxy.snmpStatus.count = countMap.get(name, 0)


    def remote_deleteDevice(self, doomed):
        """
        Allows zenhub to delete a device from our configuration
        """
        self.log.debug("Async delete device %s" % doomed)
        if doomed in self.proxies:
             del self.proxies[doomed]


    def remote_updateDeviceConfig(self, snmpTargets):
        """
        Allows zenhub to update our device configuration
        """
        self.log.debug("Device updates from zenhub received")
        self.updateDeviceConfig(snmpTargets)



    def updateDeviceConfig(self, configs):
        """
        Examine the given device configuration, and if newer update the device
        as well as its pickle file.
        If no SNMP proxy created for the device, create one.
        """

        self.log.debug("Received config for %s", configs.device)
        p = self.updateAgentProxy(configs.device, configs.connInfo)

        if self.options.cacheconfigs:
            p.lastChange = configs.lastChangeTime
            data= cPickle.dumps(configs)
            pickle_name= self.pickleName(configs.device)
            self.log.debug( "Updating cached configs in pickle file %s" % pickle_name )
            write(pickle_name, data)

        # Sanity check all OIDs and prep for eventual RRD file creation
        oidMap, p.oidMap = p.oidMap, {}
        for name, oid, path, dsType, createCmd, minmax in configs.oids:
            createCmd = createCmd.strip() # RRD create options
            oid = str(oid).strip('.')
            # beware empty OIDs
            if oid:
                oid = '.' + oid
                oid_status = oidMap.setdefault(oid, OidData())
                oid_status.update(name, path, dsType, createCmd, minmax)
                p.oidMap[oid] = oid_status

        self.proxies[configs.device] = p
        self.thresholds.updateForDevice(configs.device, configs.thresholds)



    def scanCycle(self, *unused):
        """
        """
        reactor.callLater(self.perfsnmpCycleInterval, self.scanCycle)
        self.log.debug("Getting device ping issues")
        evtSvc = self.services.get('EventService', None)
        if evtSvc:
            d = evtSvc.callRemote('getDevicePingIssues')
            d.addBoth(self.setUnresponsiveDevices)
        else:
            self.setUnresponsiveDevices('No event service')


    def setUnresponsiveDevices(self, arg):
        """
        Remember all the unresponsive devices
        """
        if isinstance(arg, list):
            deviceList = arg
            self.log.debug('unresponsive devices: %r' % deviceList)
            self.unresponsiveDevices = Set(firsts(deviceList))
        else:
            self.log.error('Could not get unresponsive devices: %s', arg)
        self.readDevices()

        
    def readDevices(self, unused=None):
        """
        Periodically fetch the performance values from all known devices
        """
        
        self.heartbeat()

        if self.status and not self.status.finished():
            _, _, _, age = self.status.stats()
            self.log.warning("There are still %d devices to query",
                             self.status.outstanding())
            self.log.warning("Problem devices: %r",
                             list(self.status.outstandingNames()))
            if age < self.perfsnmpCycleInterval * 2:
                self.log.warning("Waiting one more cycle period")
                return
            self.log.warning("Devices status is not clearing.  Restarting.")

        self.queryWorkList =  Set(self.proxies.keys())
        self.queryWorkList -= self.unresponsiveDevices
        self.status = Status()
        d = self.status.start(self.queryWorkList)
        d.addCallback(self.reportRate)
        for unused in range(MAX_SNMP_REQUESTS):
            if not self.queryWorkList: break
            d = self.startReadDevice(self.queryWorkList.pop())

            def printError(reason):
                """
                Twisted errBack to record a traceback and log messages
                """
                from StringIO import StringIO
                out = StringIO()
                reason.printTraceback(out)
                self.log.error(reason)

            d.addErrback(printError)


    def reportRate(self, *unused):
        """
        Finished reading all the devices, report stats and maybe stop
        """
        total, success, failed, runtime = self.status.stats()
        oidsRequested, self.snmpOidsRequested = self.snmpOidsRequested, 0
        self.log.info("Sent %d OID requests", oidsRequested)
        self.log.info("collected %d of %d devices in %.2f" %
                      (success, total, runtime))
        
        cycle = self.perfsnmpCycleInterval
        self.sendEvents(
            self.rrdStats.gauge('success', cycle, success) + 
            self.rrdStats.gauge('failed', cycle, failed) +
            self.rrdStats.gauge('cycleTime', cycle, runtime) +
            self.rrdStats.counter('dataPoints', cycle, self.rrd.dataPoints) +
            self.rrdStats.gauge('cyclePoints', cycle, self.rrd.endCycle())
            )
        # complain about RRD files that have not been updated
        self.checkOldFiles()

    def checkOldFiles(self):
        """
        Send an event showing whether we have old files or not
        """
        if not self.options.checkagingfiles:
            return
        self.oldFiles = Set(
            [f for f in self.oldFiles
             if os.path.exists(f) and self.oldCheck.test(f)]
            )
        if self.oldFiles:
            root = performancePath('')
            filenames = [f.lstrip(root) for f in self.oldFiles]
            message = 'RRD files not updated: ' + ' '.join(filenames)
            self.sendEvent(dict(
                dedupid="%s|%s" % (self.options.monitor, 'RRD files too old'),
                severity=Critical,
                device=self.options.monitor,
                eventClass=Status_Perf,
                summary=message))
        else:
            self.sendEvent(dict(
                severity=Clear,
                device=self.options.monitor,
                eventClass=Status_Perf,
                summary='All RRD files have been recently updated'))


    def startReadDevice(self, deviceName):
        """
        Initiate a request (or several) to read the performance data
        from a device
        """
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return

        # ensure that the request will fit in a packet
        # TODO: sanity check this number
        n = int(proxy.snmpConnInfo.zMaxOIDPerRequest)
        if proxy.singleOidMode:
            n = 1

        def getLater(oids):
            """
            Return the result of proxy.get( oids, timeoute, tries )
            """
            return checkException(self.log,
                                  proxy.get,
                                  oids,
                                  proxy.snmpConnInfo.zSnmpTimeout,
                                  proxy.snmpConnInfo.zSnmpTries)

        # Chain a series of deferred actions serially
        proxy.open()
        chain = Chain(getLater, iter(chunk(sorted(proxy.oidMap.keys()), n)))
        d = chain.run()

        def closer(arg, proxy):
            """
            Close the proxy
            """
            try:
                proxy.close()
            except Exception, ex:
                self.log.exception(ex)
                raise ex

            return arg

        d.addCallback(closer, proxy)
        d.addCallback(self.storeValues, deviceName)

        # Track the total number of OIDs requested this cycle
        self.snmpOidsRequested += len(proxy.oidMap)

        return d


    def badOid(self, deviceName, oid):
        """
        Report any bad OIDs (eg to a file log and Zenoss event) and then remove
        the OID so we dont generate any further errors.
        """
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return

        name = proxy.oidMap[oid].name
        summary = 'Error reading value for "%s" on %s (oid %s is bad)' % (
            name, deviceName, oid)
        self.sendEvent(proxy.snmpStatus.snmpStatusEvent,
                       eventClass=Perf_Snmp,
                       device=deviceName,
                       summary=summary,
                       component=name,
                       severity=Event.Debug)
        self.log.warn(summary)

        del proxy.oidMap[oid]
        

    def storeValues(self, updates, deviceName):
        """
        Decode responses from devices and store the elements in RRD files
        """

        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            self.status.record(deviceName, True)
            return

        # Look for problems
        for success, update in updates:
            # empty update is probably a bad OID in the request somewhere
            if success and not update and not proxy.singleOidMode:
                proxy.singleOidMode = True
                self.log.warn('Error collecting data on %s -- retrying in single-OID mode',
                              deviceName)
                self.startReadDevice(deviceName)
                return

            if not success:
                if isinstance(update, failure.Failure) and \
                    isinstance(update.value, error.TimeoutError):
                    self.log.debug("Device %s timed out" % deviceName)
                else:
                    self.log.warning('Failed to collect on %s (%s: %s)',
                                     deviceName,
                                     update.__class__,
                                     update)
                
        successCount = sum(firsts(updates))
        oids = []
        for success, update in updates:
            if success:
                for oid, value in update.items():
                    # should always get something back
                    if value == '' or value is None:
                        self.badOid(deviceName, oid)
                    else:
                        self.storeRRD(deviceName, oid, value)
                    oids.append(oid)

        if successCount == len(updates) and proxy.singleOidMode:
            # remove any oids that didn't report
            for doomed in Set(proxy.oidMap.keys()) - Set(oids):
                self.badOid(deviceName, doomed)

        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())

        if successCount and len(updates) > 0:
            successPercent = successCount * 100 / len(updates)
            if successPercent not in (0, 100):
                self.log.debug("Successful request ratio for %s is %2d%%",
                               deviceName,
                               successPercent)
        success = True
        if updates:
            success = successCount > 0
        self.status.record(deviceName, success)
        proxy.snmpStatus.updateStatus(deviceName, success, self.sendEvent)


    def storeRRD(self, device, oid, value):
        """
        Store a value into an RRD file

        @param device: remote device name
        @type device: string
        @param oid: SNMP OID used as our performance metric
        @type oid: string
        @param value: data to be stored
        @type value: number
        """
        oidData = self.proxies[device].oidMap.get(oid, None)
        if not oidData: return

        min, max = oidData.minmax
        try:
            value = self.rrd.save(oidData.path,
                                  value,
                                  oidData.dataStorageType,
                                  oidData.rrdCreateCommand,
                                  min=min, max=max)
        except Exception, ex:
            summary= "Unable to save data for OID %s in RRD %s" % \
                              ( oid, oidData.path )
            self.log.critical( summary )

            message= """Data was value= %s, type=%s, min=%s, max=%s
RRD create command: %s""" % \
                     ( value, oidData.dataStorageType, min, max, \
                       oidData.rrdCreateCommand )
            self.log.critical( message )
            self.log.exception( ex )

            import traceback
            trace_info= traceback.format_exc()

            evid= self.sendEvent(dict(
                dedupid="%s|%s" % (self.options.monitor, 'RRD write failure'),
                severity=Critical,
                device=self.options.monitor,
                eventClass=Status_Perf,
                component="RRD",
                oid=oid,
                path=oidData.path,
                message=message,
                traceback=trace_info,
                summary=summary))

            # For test harness purposes
            self.last_evid= evid

            # Skip thresholds
            return

        for ev in self.thresholds.check(oidData.path, time.time(), value):
            eventKey = oidData.path.rsplit('/')[-1]
            if ev.has_key('eventKey'):
                ev['eventKey'] = '%s|%s' % (eventKey, ev['eventKey'])
            else:
                ev['eventKey'] = eventKey
            self.sendThresholdEvent(**ev)



    def connected(self):
        """
        Run forever, fetching and storing
        """
        self.log.debug( "Connected to zenhub" )
        d = drive(self.startUpdateConfig)
        d.addCallbacks(self.scanCycle, self.errorStop)


    def buildOptions(self):
        """
        Build a list of command-line options
        """
        SnmpDaemon.buildOptions(self)
        self.parser.add_option('--checkAgingFiles',
                               dest='checkagingfiles',
                               action="store_true",
                               default=False,
                               help="Send events when RRD files are not being updated regularly")

        self.parser.add_option('--cacheconfigs',
                               dest='cacheconfigs',
                               action="store_true",
                               default=False,
                               help="To improve startup times, cache configuration received from zenhub")


if __name__ == '__main__':
    # The following bizarre include is required for PB to be happy
    from Products.ZenRRD.zenperfsnmp import zenperfsnmp

    zpf = zenperfsnmp()
    zpf.run()

