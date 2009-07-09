#! /usr/bin/env python
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__= """zenprocess

Gets SNMP process data from a device's HOST-RESOURCES-MIB
and store process performance in RRD files.
"""

import sys
import logging
import time
from sets import Set

log = logging.getLogger("zen.zenprocess")

from twisted.internet import reactor, defer, error
from twisted.spread import pb

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.NJobs import NJobs
from Products.ZenUtils.Chain import Chain
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp, \
      Status_OSProcess, Critical, Status_Perf

from Products.ZenRRD.RRDUtil import RRDUtil
from SnmpDaemon import SnmpDaemon

from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
# needed for pb comms
SnmpConnInfo = SnmpConnInfo # Shut up, pyflakes!

# HOST-RESOURCES-MIB OIDs used
HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.2'
PATHTABLE = RUNROOT + '.2.1.4'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

DEFAULT_PARALLEL_JOBS = 10

# Max size for CPU numbers
WRAP = 0xffffffffL

def reverseDict(d):
    """
    Return a dictionary with keys and values swapped:
    all values are lists to handle the different keys mapping to the same value
    """
    result = {}
    for a, v in d.items():
        result.setdefault(v, []).append(a)
    return result

def chunk(lst, n):
    """
    Break lst into n-sized chunks
    """
    return [lst[i:i+n] for i in range(0, len(lst), n)]

class ScanFailure(Exception): pass

class Pid:
    """
    Helper class to track process id information
    """
    cpu = None
    memory = None

    def updateCpu(self, n):
        """
        """
        if n is not None:
            try:
                n = int(n)
            except ValueError, er:
                log.warning("Bad value for CPU: '%s'", n)

        if self.cpu is None or n is None:
            self.cpu = n
            return None
        diff = n - self.cpu
        if diff < 0:
            # don't provide a value when the counter falls backwards
            n = None
            diff = None
        self.cpu = n
        return diff

    def updateMemory(self, n):
        """
        """
        self.memory = n

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return '<Pid> memory: %s cpu: %s' % (self.memory, self.cpu)
    __repr__ = __str__


class Process(pb.Copyable, pb.RemoteCopy):
    """
    Track process-specific configuration data
    """
    name = None
    originalName = None
    ignoreParameters = False
    restart = None
    severity = Event.Warning
    status = 0
    cpu = 0
    cycleTime = None

    def __init__(self):
        self.pids = {}

    def match(self, name, args):
        """
        Perform exact comparisons on the process names.

        @parameter name: name of a process to compare
        @type name: string
        @parameter args: argument list of the process
        @type args: string
        @return: does the name match this process's info?
        @rtype: Boolean
        """
        if self.name is None:
            return False
        if self.ignoreParameters or not args:
            return self.originalName == name
        return self.originalName == '%s %s' % (name, args)

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return str(self.name)
    __repr__ = __str__

    def updateCpu(self, pid, value):
        """
        """
        p = self.pids.setdefault(pid, Pid())
        cpu = p.updateCpu(value)
        if cpu is not None:
            self.cpu += cpu
            self.cpu %= WRAP

    def getCpu(self):
        """
        """
        return self.cpu

    def updateMemory(self, pid, value):
        """
        """
        self.pids.setdefault(pid, Pid()).memory = value

    def getMemory(self):
        """
        """
        return sum([x.memory for x in self.pids.values()
                    if x.memory is not None])

    def discardPid(self, pid):
        """
        """
        if pid in self.pids:
            del self.pids[pid]

    def updateConfig(self, update):
        """
        """
        if self is update:
            return
        self.name = update.name
        self.originalName = update.originalName
        self.ignoreParameters = update.ignoreParameters
        self.restart = update.restart
        self.severity = update.severity

pb.setUnjellyableForClass(Process, Process)


class Device(pb.Copyable, pb.RemoteCopy):
    """
    Track device data
    """
    name = ''
    snmpConnInfo = None
    proxy = None
    lastScan = 0.
    snmpStatus = 0
    lastChange = 0
    maxOidsPerRequest = 40

    def __init__(self):
        # map process name to Process object above
        self.processes = {}
        # map pid number to Process object
        self.pids = {}

    def open(self):
        """
        Create a connection to the remote device
        """
        if (self.proxy is None or \
            self.proxy.snmpConnInfo != self.snmpConnInfo):
            self.proxy = self.snmpConnInfo.createSession()
            self.proxy.open()

    def close(self, unused=None):
        """
        Close down the connection to the remote device
        """
        if self.proxy:
            self.proxy.close()
        self.proxy = None
        return unused

    def updateConfig(self, cfg):
        """
        Called with configuration information from zenhub.
        """
        if self is cfg:
            return
        log.debug("Updating configuration for %s",
            update.name)
        self.snmpConnInfo = cfg.snmpConnInfo
        unused = Set(self.processes.keys())
        for update in cfg.processes.values():
            unused.discard(update.name)
            p = self.processes.setdefault(update.name, Process())
            p.updateConfig(update)
        for name in unused:
            del self.processes[name]


    def get(self, oids):
        """
        Perform SNMP get for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        return self.proxy.get(oids,
                              self.snmpConnInfo.zSnmpTimeout,
                              self.snmpConnInfo.zSnmpTries)


    def getTables(self, oids):
        """
        Perform SNMP getTable for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        repetitions = self.maxOidsPerRequest / len(oids)
        t = self.proxy.getTable(oids,
                                timeout=self.snmpConnInfo.zSnmpTimeout,
                                retryCount=self.snmpConnInfo.zSnmpTries,
                                maxRepetitions=repetitions,
                                limit=sys.maxint)
        return t
pb.setUnjellyableForClass(Device, Device)


class zenprocess(SnmpDaemon):
    """
    Daemon class to connect to an SNMP agent and determine the processes
    that are running on that server.
    """
    statusEvent = { 'eventClass' : Status_OSProcess,
                    'eventGroup' : 'Process' }
    initialServices = SnmpDaemon.initialServices + ['ProcessConfig']
    processConfigInterval = 20*60
    processCycleInterval = 5*60
    properties = SnmpDaemon.properties + ('processCycleInterval',)
    missing = 0
    restarted = 0
    parallelJobs = DEFAULT_PARALLEL_JOBS

    def __init__(self, noopts=False):
        SnmpDaemon.__init__(self, 'zenprocess', noopts)
        self._devices = {}
        self.scanning = None
        self.downDevices = Set()

    def devices(self):
        """
        Return the list of devices that are available

        @return: device list
        @rtype: dictionary of device name, device object
        """
        return dict([(k, v) for k, v in self._devices.items()
                     if k not in self.downDevices])

    def fetchConfig(self):
        """
        Get configuration values from zenhub

        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        def doFetchConfig(driver):
            now = time.time()

            yield self.model().callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            yield self.model().callRemote('getZenProcessParallelJobs')
            self.parallelJobs = int(driver.next())

            yield self.model().callRemote('propertyItems')
            self.setPropertyItems(driver.next())

            self.rrd = RRDUtil(createCommand, self.processCycleInterval)

            yield self.model().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())

            yield self.model().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor,
                                 self.name,
                                 driver.next(),
                                 createCommand)

            devices = []
            if self.options.device:
                devices = [self.options.device]
            yield self.model().callRemote('getOSProcessConf', devices)
            driver.next()
            self.sendEvents(
                self.rrdStats.gauge('configTime',
                                    self.processConfigInterval,
                                    time.time() - now)
                )

        return drive(doFetchConfig)

    def remote_deleteDevice(self, doomed):
        """
        Called from zenhub to remove a device from our configuration

        @parameter doomed: device to delete
        @type doomed: string
        """
        self.log.debug("zenhub asks us to delete device %s" % doomed)
        if doomed in self._devices:
             del self._devices[doomed]
        self.clearSnmpError(doomed, "Device %s removed from SNMP collection")

    def remote_updateDeviceList(self, devices):
        """
        Called from zenhub to update the devices to monitor

        @parameter devices: devices to monitor
        @type devices: list of (device, changetime) tuples
        """
        self.log.debug("Received updated device list from zenhub %s" % devices)
        doomed = Set(self._devices.keys())
        updated = []
        for device, lastChange in devices:
            # Ignore updates for devices if we've only asked for one device
            if self.options.device and \
               device != self.options.device:
                self.log.debug("Ignoring update for %s as we only want %s",
                               device, self.options.device)
                continue

            cfg = self._devices.get(device, None)
            if not cfg or self._devices[device].lastChange < lastChange:
                updated.append(device)
            doomed.discard(device)

        if updated:
            log.info("Fetching the config for %s", updated)
            d = self.model().callRemote('getOSProcessConf', devices)
            d.addCallback(self.updateDevices, updated)
            d.addErrback(self.error)

        if doomed:
            log.info("Removing %s", doomed)
            for device in doomed:
                del self._devices[device]
                self.clearSnmpError(device, "device %s removed" % device)


    def clearSnmpError(self, name, message):
        """
        Send an event to clear other events.

        @parameter name: device for which the event applies
        @type name: string
        @parameter message: clear text
        @type message: string
        """
        if name in self._devices:
            if self._devices[name].snmpStatus > 0:
                self._devices[name].snmpStatus = 0
                self.sendEvent(self.statusEvent,
                               eventClass=Status_Snmp,
                               component="process",
                               device=name,
                               summary=message,
                               agent='zenprocess',
                               severity=Event.Clear)


    def remote_updateDevice(self, cfg):
        """
        Twisted remote callback, to allow zenhub to remotely update
        this daemon.

        @parameter cfg: configuration information returned from zenhub
        @type cfg: object
        """
        self.log.debug("Configuration update from zenhub for %s", cfg.name)
        self.updateDevices([cfg],[])


    def updateDevices(self, cfgs, fetched):
        """
        Called when the zenhub service getSnmpStatus completes.

        @parameter cfgs: configuration information returned from zenhub
        @type cfgs: list of objects
        @parameter fetched: names we want zenhub to return information about
        @type fetched: list of strings
        """
        received = Set()
        for cfg in cfgs:
            received.add(cfg.name)
            d = self._devices.setdefault(cfg.name, cfg)
            d.updateConfig(cfg)
            self.thresholds.updateForDevice(cfg.name, cfg.thresholds)

        for doomed in Set(fetched) - received:
            if doomed in self._devices:
                del self._devices[doomed]

    def start(self, driver):
        """
        Read the basic config needed to do anything, and to reread
        the configuration information on a periodic basis.
        """
        log.debug("Fetching configuration from zenhub")
        devices = self._devices.keys()
        yield self.fetchConfig()
        self.updateDevices(driver.next(), devices)

        yield self.model().callRemote('getSnmpStatus', self.options.device)
        self.updateSnmpStatus(driver.next())

        yield self.model().callRemote('getProcessStatus', self.options.device)
        self.updateProcessStatus(driver.next())

        driveLater(self.configCycleInterval * 60, self.start)


    def updateSnmpStatus(self, updates):
        """
        Called when the zenhub service getSnmpStatus completes.

        @parameter updates: List of names and error counts
        @type updates: list of (string, int)
        """
        for name, count in updates:
            d = self._devices.get(name)
            if d:
                d.snmpStatus = count


    def updateProcessStatus(self, status):
        """
        Called when the zenhub service getProcessStatus completes.

        @parameter status: List of names, component names and error counts
        @type status: list of (string, string, int)
        """
        down = {}
        for device, component, count in status:
            down[ (device, component) ] = count
        for name, device in self._devices.items():
            for p in device.processes.values():
                p.status = down.get( (name, p.originalName), 0)


    def oneDevice(self, device):
        """
        Contact one device and return a deferred which gathers data from
        the device.

        @parameter device: proxy object to the remote computer
        @type device: Device object
        @return: job to scan a device
        @rtype: Twisted deferred object
        """
        def go(driver):
            """
            Generator object to gather information from a device.
            """
            try:
                device.open()
                yield self.scanDevice(device)
                driver.next()

                # Only fetch performance data if status data was found.
                if device.snmpStatus == 0:
                    yield self.fetchPerf(device)
                    driver.next()
                else:
                    log.warn("Failed to find performance data for %s",
                             device.name)
            except:
                log.debug('Failed to scan device %s' % device.name)

        def close(res):
            """
            Twisted closeBack and errBack function which closes any
            open connections.
            """
            try:
                device.close()
            except:
                log.debug("Failed to close device %s" % device.name)

        d = drive(go)
        d.addBoth(close)
        return d


    def scanDevice(self, device):
        """
        Fetch all the process info for a device using SNMP table gets

        @parameter device: proxy connection object
        @type device: Device object
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        device.lastScan = time.time()
        tables = [NAMETABLE, PATHTABLE, ARGSTABLE]
        d = device.getTables(tables)
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d


    def deviceFailure(self, reason, device):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        @parameter device: proxy connection object
        @type device: Device object
        """
        self.sendEvent(self.statusEvent,
                       eventClass=Status_Snmp,
                       component="process",
                       device=device.name,
                       summary='Unable to read processes on device %s' % device.name,
                       severity=Event.Error)
        device.snmpStatus += 1
        if isinstance(reason.value, error.TimeoutError):
            self.log.debug('Timeout on device %s' % device.name)
        else:
            self.logError('Error on device %s' % device.name, reason.value)

    def mapResultsToDicts(self, results):
        """
        Parse the process tables and reconstruct the list of processes
        that are on the device.

        @parameter results: results of SNMP table gets ie (OID + pid, value)
        @type results: dictionary of dictionaries
        @return: maps relating names and pids to each other
        @rtype: dictionary, dictionary, dictionary, list of tuples
        """
        def extract(dictionary, oid, value):
            """
            Helper function to extract SNMP table data.
            """
            pid = int(oid.split('.')[-1])
            dictionary[pid] = value

        names, paths, args = {}, {}, {}
        if self.options.showrawtables:
            log.info("NAMETABLE = %r", results[NAMETABLE])
        for row in results[NAMETABLE].items():
            extract(names, *row)

        if self.options.showrawtables:
            log.info("PATHTABLE = %r", results[PATHTABLE])
        for row in results[PATHTABLE].items():
            extract(paths, *row)

        if self.options.showrawtables:
            log.info("ARGSTABLE = %r", results[ARGSTABLE])
        for row in results[ARGSTABLE].items():
            extract(args,  *row)

        procs = []
        for pid, path in paths.items():
            if pid not in names: continue
            name = names[pid]
            if path and path.find('\\') == -1:
                name = path
            arg = args.get(pid, '')
            procs.append( (pid, (name, arg) ) )

        return names, paths, args, procs

    def showProcessList(self, device_name, procs):
        """
        Display the processes in a sane manner.

        @parameter device_name: name of the device
        @type device_name: string
        @parameter procs: list of (pid, (name, args))
        @type procs: list of tuples
        """
        proc_list = [ '%s %s %s' % (pid, name, args) for pid, (name, args) \
                         in sorted(procs)]
        proc_list.append('')
        log.info("#===== Processes on %s:\n%s", device_name, '\n'.join(proc_list))

    def storeProcessNames(self, results, device):
        """
        Parse the process tables and reconstruct the list of processes
        that are on the device.

        @parameter results: results of SNMP table gets
        @type results: dictionary of dictionaries
        @parameter device: proxy connection object
        @type device: Device object
        """
        if not results or not results[NAMETABLE]:
            summary = 'Device %s does not publish HOST-RESOURCES-MIB' % device.name
            resolution="Verify with snmpwalk -v1 -c community %s %s" % (
                device.name, NAMETABLE )
            self.sendEvent(self.statusEvent,
                           device=device.name,
                           summary=summary,
                           resolution=resolution,
                           severity=Event.Error)
            log.info(summary)
            return
        if device.snmpStatus > 0:
            summary = 'Process table up for device %s' % device.name
            self.clearSnmpError(device.name, summary)

        names, paths, args, procs = self.mapResultsToDicts(results)
        if self.options.showprocs:
            self.showProcessList(device.name, procs)

        # look for changes in processes
        before = Set(device.pids.keys())
        after = {}
        for p in device.processes.values():
            for pid, (name, args) in procs:
                if p.match(name, args):
                    log.debug("Found process %d on %s" % (pid, p.name))
                    after[pid] = p
        afterSet = Set(after.keys())
        afterByConfig = reverseDict(after)
        new =  afterSet - before
        dead = before - afterSet

        # report pid restarts
        restarted = {}
        for p in dead:
            config = device.pids[p]
            config.discardPid(p)
            if config in afterByConfig:
                self.restarted += 1
                if config.restart:
                    restarted[config] = True
                    summary = 'Process restarted: %s' % config.originalName
                    self.sendEvent(self.statusEvent,
                                   device=device.name,
                                   summary=summary,
                                   component=config.originalName,
                                   severity=config.severity)
                    log.info(summary)

        # report alive processes
        for config, pids in afterByConfig.items():
            if config in restarted: continue
            summary = "Process up: %s" % config.originalName
            self.sendEvent(self.statusEvent,
                           device=device.name,
                           summary=summary,
                           component=config.originalName,
                           severity=Event.Clear)
            config.status = 0
            log.debug(summary)

        for p in new:
            log.debug("Found new %s pid %d on %s" % (
                after[p].originalName, p, device.name))
        device.pids = after

        # Look for missing processes
        for config in device.processes.values():
            if config not in afterByConfig:
                self.missing += 1
                config.status += 1
                summary = 'Process not running: %s' % config.originalName
                self.sendEvent(self.statusEvent,
                               device=device.name,
                               summary=summary,
                               component=config.originalName,
                               severity=config.severity)
                log.warning(summary)

        # Store per-device, per-process statistics
        pidCounts = dict([(p, 0) for p in device.processes])
        for pids, pidConfig in device.pids.items():
            pidCounts[pidConfig.name] += 1
        for name, count in pidCounts.items():
            self.save(device.name, name, 'count_count', count, 'GAUGE')


    def periodic(self, unused=None):
        """
        Main loop that drives all other processing.
        """
        reactor.callLater(self.processCycleInterval, self.periodic)

        if self.scanning:
            running, unstarted, finished = self.scanning.status()
            runningDevices = [ d.name for d in self.devices().values() \
                    if d.proxy is not None]

            if runningDevices or unstarted > 0:
                log.warning("Process scan not finishing: "
                    "%d running, %d waiting, %d finished" % (
                        running, unstarted, finished))
                log.warning("Problem devices: %r", runningDevices)
                return

        start = time.time()

        def doPeriodic(driver):
            """
            Generator function to create deferred jobs.
            """
            yield self.getDevicePingIssues()
            self.downDevices = Set([d[0] for d in driver.next()])

            self.scanning = NJobs(self.parallelJobs,
                                  self.oneDevice,
                                  self.devices().values())
            yield self.scanning.start()
            driver.next()

        def checkResults(results):
            """
            Process the results from all deferred objects.
            """
            for result in results:
                if isinstance(result , Exception):
                    log.error("Error scanning device: %s", result)
                    break
            self.cycleTime = time.time() - start
            self.heartbeat()

        drive(doPeriodic).addCallback(checkResults)


    def fetchPerf(self, device):
        """
        Get performance data for all the monitored processes on a device

        @parameter device: proxy object to the remote computer
        @type device: Device object
        """
        oids = []
        for pid, pidConf in device.pids.items():
            oids.extend([CPU + str(pid), MEM + str(pid)])
        if not oids:
            return defer.succeed(([], device))

        d = Chain(device.get, iter(chunk(oids, device.maxOidsPerRequest))).run()
        d.addCallback(self.storePerfStats, device)
        d.addErrback(self.deviceFailure, device)
        return d


    def storePerfStats(self, results, device):
        """
        Save the process performance data in RRD files

        @parameter results: results of SNMP table gets
        @type results: list of (success, result) tuples
        @parameter device: proxy object to the remote computer
        @type device: Device object
        """
        for success, result in results:
            if not success:
                self.deviceFailure(result, device)
                return results
        self.clearSnmpError(device.name,
                            'Process table up for device %s' % device.name)
        parts = {}
        for success, values in results:
            if success:
                parts.update(values)
        results = parts
        byConf = reverseDict(device.pids)
        for pidConf, pids in byConf.items():
            if len(pids) != 1:
                log.info("There are %d pids by the name %s",
                         len(pids), pidConf.name)
            pidName = pidConf.name
            for pid in pids:
                cpu = results.get(CPU + str(pid), None)
                mem = results.get(MEM + str(pid), None)
                pidConf.updateCpu(pid, cpu)
                pidConf.updateMemory(pid, mem)
            self.save(device.name, pidName, 'cpu_cpu', pidConf.getCpu(),
                      'DERIVE', min=0)
            self.save(device.name, pidName, 'mem_mem', pidConf.getMemory() * 1024,
                      'GAUGE')


    def save(self, deviceName, pidName, statName, value, rrdType,
             min='U', max='U'):
        """
        Save a value into an RRD file

        @param deviceName: name of the remote device (ie a hostname)
        @type deviceName: string
        @param pidName: process id of the monitored process
        @type pidName: string
        @param statName: metric name
        @type statName: string
        @param value: data to be stored
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        @param min: minimum value acceptable for this metric
        @type min: number
        @param max: maximum value acceptable for this metric
        @type max: number
        """
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
        try:
            value = self.rrd.save(path, value, rrdType, min=min, max=max)

        except Exception, ex:
            summary= "Unable to save data for process-monitor RRD %s" % \
                              path
            self.log.critical( summary )

            message= "Data was value= %s, type=%s, min=%s, max=%s" % \
                     ( value, rrdType, min, max, )
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
                pidName=pidName,
                statName=statName,
                path=path,
                message=message,
                traceback=trace_info,
                summary=summary))

            # Skip thresholds
            return

        for ev in self.thresholds.check(path, time.time(), value):
            self.sendThresholdEvent(**ev)


    def heartbeat(self):
        """
        Twisted keep-alive mechanism to ensure that
        we're still connected to zenhub.
        """
        self.scanning = None
        devices = self.devices()
        pids = sum(map(lambda x: len(x.pids), devices.values()))
        log.info("Pulled process status for %d devices and %d processes",
                 len(devices), pids)
        SnmpDaemon.heartbeat(self)
        cycle = self.processCycleInterval
        self.sendEvents(
            self.rrdStats.counter('dataPoints', cycle, self.rrd.dataPoints) +
            self.rrdStats.gauge('cyclePoints', cycle, self.rrd.endCycle()) +
            self.rrdStats.gauge('pids', cycle, pids) +
            self.rrdStats.gauge('devices', cycle, len(devices)) +
            self.rrdStats.gauge('missing', cycle, self.missing) +
            self.rrdStats.gauge('restarted', cycle, self.restarted) +
            self.rrdStats.gauge('cycleTime', cycle, self.cycleTime)
            )


    def connected(self):
        """
        Gather our configuration and start collecting status information.
        Called after connected to the zenhub service.
        """
        drive(self.start).addCallbacks(self.periodic, self.errorStop)


    def buildOptions(self):
        """
        Build a list of command-line options
        """
        SnmpDaemon.buildOptions(self)
        self.parser.add_option('--showprocs',
                               dest='showprocs',
                               action="store_true",
                               default=False,
                               help="Show the list of processes found." \
                                    "For debugging purposes only.")
        self.parser.add_option('--showrawtables',
                               dest='showrawtables',
                               action="store_true",
                               default=False,
                               help="Show the raw SNMP processes data returned " \
                                    "from the device. For debugging purposes only.")


if __name__ == '__main__':
    # Needed for PB communications
    from Products.ZenRRD.zenprocess import zenprocess
    z = zenprocess()
    z.run()
