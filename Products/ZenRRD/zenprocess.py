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

import Globals
import logging
import sys

import zope.component
import zope.interface

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
    IScheduledTask, IEventService, IDataService
from Products.ZenCollector.tasks import SimpleTaskFactory, SimpleTaskSplitter,\
    TaskStates
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp, Status_OSProcess, \
        Status_Perf
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenUtils.Chain import Chain

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenUtils.Utils import unused
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)
from Products.ZenHub.services.ProcessConfig import ProcessProxy
unused(ProcessProxy)
from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
unused(SnmpConnInfo)

from twisted.internet import defer, error
from twisted.python.failure import Failure

log = logging.getLogger("zen.zenprocess")

# HOST-RESOURCES-MIB OIDs used
HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.2'
PATHTABLE = RUNROOT + '.2.1.4'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

# Max size for CPU numbers
WRAP = 0xffffffffL

# Create an implementation of the ICollectorPreferences interface so that the
# ZenCollector framework can configure itself from our preferences.
class ZenProcessPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new ZenProcessPreferences instance and provide default
        values for needed attributes.
        """
        self.collectorName = "zenprocess"
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        
        #will be updated based on Performance Config property of same name
        self.processCycleInterval = 3 * 60
        
        #will be filled in based on buildOptions
        self.options = None

        # the configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.ProcessConfig'

    @property
    def cycleInterval(self):
        """
        defined as a property since it is needed by the interface    
        """
        return self.processCycleInterval
    
    def buildOptions(self, parser):
        """
        Build a list of command-line options
        """
        parser.add_option('--showprocs',
                            dest='showprocs',
                            action="store_true",
                            default=False,
                            help="Show the list of processes found." \
                                "For debugging purposes only.")
        parser.add_option('--showrawtables',
                            dest='showrawtables',
                            action="store_true",
                            default=False,
                            help="Show the raw SNMP processes data returned " \
                                "from the device. For debugging purposes only.")

    def postStartup(self):
        pass

class DeviceStats:
    def __init__(self, deviceProxy):
        self.config = deviceProxy
        # map pid number to ProcessStats object
        self._pidToProcess = {}
        # map ProcessProxy id to ProcessStats object
        self._processes = {}
        for id, process in deviceProxy.processes.items():
            self._processes[id] = ProcessStats(process)

    def update(self, deviceProxy):
        unused = set(self._processes.keys())
        for id, process in deviceProxy.processes.items():
            unused.discard(id)
            if self._processes.get(id):
                self._processes[id].update(process)
            else:
                self._processes[id] = ProcessStats(process)
            
        #delete the left overs
        for id in unused:
            del self.processes[id]

    @property
    def processStats(self):
        """
        The ProcessStats: processes configured to be monitored
        """
        return self._processes.values()

    @property
    def pids(self):
        """
        returns the pids from being tracked
        """
        return self._pidToProcess.keys()
    
    @property
    def monitoredProcs(self):
        """
        returns ProcessStats for which we have a pid
        """
        return self._pidToProcess.values()

class ProcessStats:
    def __init__(self, processProxy):
        self._pids={}
        self._config = processProxy
        self.cpu = 0

    def update(self, processProxy):
        self._config = processProxy

    def __str__(self):
        """
        Override the Python default to represent ourselves as a string
        """
        return str(self._config.name)
    __repr__ = __str__

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
        if self._config.name is None:
            return False
        if self._config.ignoreParameters or not args:
            return self._config.originalName == name
        return self._config.originalName == '%s %s' % (name, args)
    
    def updateCpu(self, pid, value):
        """
        """
        pid = self._pids.setdefault(pid, Pid())
        cpu = pid.updateCpu(value)
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
        self._pids.setdefault(pid, Pid()).memory = value

    def getMemory(self):
        """
        """
        return sum([x.memory for x in self._pids.values()
                    if x.memory is not None])

    def discardPid(self, pid):
        """
        """
        if pid in self._pids:
            del self._pids[pid]

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
            except ValueError:
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

# Create an implementation of the IScheduledTask interface that will perform
# the actual collection work needed by this collector.
class ZenProcessTask(ObservableMixin):
    """
    A scheduled task that finds instances of configure processes and collects 
    metrics on the processes 
    """
    zope.interface.implements(IScheduledTask)
    
    #Keep state about process stats across task updates
    DEVICE_STATS = {}
    
    #counter to keep track of total restarted and missing processes
    RESTARTED = 0
    MISSING = 0 
    
    STATE_CONNECTING = 'CONNECTING'
    STATE_SCANNING_PROCS = 'SCANNING_PROCESSES'
    STATE_FETCH_PERF = 'FETCH_PERF_DATA'
    STATE_STORE_PERF = 'STORE_PERF_DATA'
    
    statusEvent = { 'eventClass' : Status_OSProcess,
                    'eventGroup' : 'Process' }
    
    def __init__(self,
                 deviceId,
                 taskName,
                 scheduleIntervalSeconds,
                 taskConfig):
        super(ZenProcessTask, self).__init__()

        #needed for interface
        self.name = taskName
        self.configId = deviceId
        self.interval = scheduleIntervalSeconds
        self.state = TaskStates.STATE_IDLE

        #the task config corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = self._device.name
        self._manageIp = self._device.manageIp
        self._maxOidsPerRequest = self._device.zMaxOIDPerRequest
        
        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        "zenprocess")
        self.snmpProxy = None
        self.snmpConnInfo = self._device.snmpConnInfo
        
        self._deviceStats = ZenProcessTask.DEVICE_STATS.get(self._devId)
        if self._deviceStats:
            self._deviceStats.update(self._device)
        else:
            self._deviceStats = DeviceStats(self._device)
            ZenProcessTask.DEVICE_STATS[self._devId] = self._deviceStats
        
    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        msg = 'Unable to read processes on device %s' % self._devId
        self._eventService.sendEvent(self.statusEvent,
                                     eventClass=Status_Snmp,
                                     component="process",
                                     device=self._devId,
                                     summary=msg,
                                     severity=Event.Error)

        if isinstance(reason.value, error.TimeoutError):
            log.debug('Timeout on device %s' % self._devId)
        else:
            log.error('Error on device %s' % self._devId, reason.value)
        return reason
        
        
    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote device.
        """
        log.debug("Connected to %s [%s]", self._devId, self._manageIp)
        return result

    def _collectCallback(self, result):
        """
        Callback called after a connect or previous collection so that another
        collection can take place.
        """
        log.debug("scanning for processes from %s [%s]", 
                  self._devId, self._manageIp)
        
        self.state = ZenProcessTask.STATE_SCANNING_PROCS
        tables = [NAMETABLE, PATHTABLE, ARGSTABLE]
        d = self._getTables(tables)
        d.addCallbacks(self._storeProcessNames, self._failure)
        d.addCallback(self._fetchPerf)
        return d
    
    def _finished(self, result):
        """
        Callback activated when the task is complete
        """
        if not isinstance(result, Failure):
            log.debug("Device %s [%s] scanned successfully",
                      self._devId, self._manageIp)
        else:
            log.debug("Device %s [%s] scanned failed, %s",
                      self._devId, self._manageIp, result.getErrorMessage())
        
        try:
            self._close()
        except Exception, e:
            log.warn("Failed to close device %s: error %s" % 
                     (self._devId, str(e)))
        # give the result to the rest of the callback/errchain so that the
        # ZenCollector framework can keep track of the success/failure rate
        return result


    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: job to scan a device
        @rtype: Twisted deferred object
        """

        # see if we need to connect first before doing any collection
        d = defer.maybeDeferred(self._connect)
        d.addCallbacks(self._connectCallback, self._failure)
        d.addCallback(self._collectCallback)

        # Add the _finished callback to be called in both success and error
        # scenarios.
        d.addBoth(self._finished)

        # returning a Deferred will keep the framework from assuming the task
        # is done until the Deferred actually completes
        return d

    def _storeProcessNames(self, results):
        """
        Parse the process tables and reconstruct the list of processes
        that are on the device.

        @parameter results: results of SNMP table gets
        @type results: dictionary of dictionaries
        @parameter device: proxy connection object
        @type device: Device object
        """
        
        if not results or not results[NAMETABLE]:
            summary = 'Device %s does not publish HOST-RESOURCES-MIB' % \
                        self._devId
            resolution="Verify with snmpwalk -v1 -c community %s %s" % \
                        (self._devId, NAMETABLE )
            
            self._eventService.sendEvent(self.statusEvent,
                                         device=self._devId,
                                         summary=summary,
                                         resolution=resolution,
                                         severity=Event.Error)
            log.info(summary)
            return defer.fail(summary)
        
        summary = 'Process table up for device %s' % self._devId
        self._clearSnmpError(summary)

        showrawtables = self._preferences.options.showrawtables
        args, procs = mapResultsToDicts(showrawtables, results)
        if self._preferences.options.showprocs:
            self._showProcessList( procs )

        # look for changes in processes
        beforePids = set(self._deviceStats.pids)
        afterPidToProcessStats = {}
        for pStats in self._deviceStats.processStats:
            for pid, (name, args) in procs:
                if pStats.match(name, args):
                    log.debug("Found process %d on %s" % (pid, 
                                                          pStats._config.name))
                    afterPidToProcessStats[pid] = pStats
        afterPids = set(afterPidToProcessStats.keys())
        afterByConfig = reverseDict(afterPidToProcessStats)
        newPids =  afterPids - beforePids
        deadPids = beforePids - afterPids

        # report pid restarts
        restarted = {}
        for pid in deadPids:
            procStats = self._deviceStats._pidToProcess[pid]
            procStats.discardPid(pid)
            if procStats in afterByConfig:
                ZenProcessTask.RESTARTED += 1
                pConfig = procStats._config
                if pConfig.restart:
                    restarted[procStats] = True
                    
                    summary = 'Process restarted: %s' % pConfig.originalName
                    
                    self._eventService.sendEvent(self.statusEvent,
                                                 device=self._devId,
                                                 summary=summary,
                                                 component=pConfig.originalName,
                                                 severity=pConfig.severity)
                    log.info(summary)

        # report alive processes
        for processStat in afterByConfig.keys():
            if processStat in restarted: continue
            summary = "Process up: %s" % processStat._config.originalName
            self._eventService.sendEvent(self.statusEvent,
                                         device=self._devId,
                                         summary=summary,
                                         component=processStat._config.originalName,
                                         severity=Event.Clear)
            log.debug(summary)

        for pid in newPids:
            log.debug("Found new %s pid %d on %s" % (
                afterPidToProcessStats[pid]._config.originalName, pid, 
                self._devId))
        
        self._deviceStats._pidToProcess = afterPidToProcessStats

        # Look for missing processes
        for procStat in self._deviceStats.processStats:
            if procStat not in afterByConfig:
                procConfig = procStat._config
                ZenProcessTask.MISSING += 1
                summary = 'Process not running: %s' % procConfig.originalName
                self._eventService.sendEvent(self.statusEvent,
                                             device=self._devId,
                                             summary=summary,
                                             component=procConfig.originalName,
                                             severity=procConfig.severity)
                log.warning(summary)

        # Store per-device, per-process statistics
        pidCounts = dict([(p, 0) for p in self._deviceStats.processStats])
        for procStat in self._deviceStats.monitoredProcs:
            pidCounts[procStat] += 1
        for procName, count in pidCounts.items():
            self._save(procName, 'count_count', count, 'GAUGE')
        return results

    def _fetchPerf(self, results):
        """
        Get performance data for all the monitored processes on a device

        @parameter device: proxy object to the remote computer
        @type device: Device object
        """
        self.state = ZenProcessTask.STATE_FETCH_PERF

        oids = []
        for pid in self._deviceStats.pids:
            oids.extend([CPU + str(pid), MEM + str(pid)])
        if not oids:
            return defer.succeed(([]))
        d = Chain(self._get, iter(chunk(oids, self._maxOidsPerRequest))).run()
        d.addCallback(self._storePerfStats)
        d.addErrback(self._failure)
        return d

    def _storePerfStats(self, results):
        """
        Save the process performance data in RRD files

        @parameter results: results of SNMP table gets
        @type results: list of (success, result) tuples
        @parameter device: proxy object to the remote computer
        @type device: Device object
        """
        self.state = ZenProcessTask.STATE_STORE_PERF
        for success, result in results:
            if  not success:
                #return the failure
                return result
        self._clearSnmpError('Process table up for device %s' % self._devId)
        parts = {}
        for success, values in results:
            if success:
                parts.update(values)
        results = parts
        byConf = reverseDict(self._deviceStats._pidToProcess)
        for procStat, pids in byConf.items():
            if len(pids) != 1:
                log.info("There are %d pids by the name %s",
                         len(pids), procStat.name)
            procName = procStat._config.name
            for pid in pids:
                cpu = results.get(CPU + str(pid), None)
                mem = results.get(MEM + str(pid), None)
                procStat.updateCpu(pid, cpu)
                procStat.updateMemory(pid, mem)
            self._save(procName, 'cpu_cpu', procStat.getCpu(),
                      'DERIVE', min=0)
            self._save(procName, 'mem_mem', 
                      procStat.getMemory() * 1024, 'GAUGE')
        return results

    def _getTables(self, oids):
        """
        Perform SNMP getTable for specified OIDs
        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        repetitions = self._maxOidsPerRequest / len(oids)
        t = self.snmpProxy.getTable(oids,
                                timeout=self.snmpConnInfo.zSnmpTimeout,
                                retryCount=self.snmpConnInfo.zSnmpTries,
                                maxRepetitions=repetitions,
                                limit=sys.maxint)
        return t

    def _get(self, oids):
        """
        Perform SNMP get for specified OIDs

        @parameter oids: OIDs to gather
        @type oids: list of strings
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        return self.snmpProxy.get(oids,
                              self.snmpConnInfo.zSnmpTimeout,
                              self.snmpConnInfo.zSnmpTries)

    def _connect(self):
        """
        Create a connection to the remote device
        """
        self.state = ZenProcessTask.STATE_CONNECTING
        if (self.snmpProxy is None or 
            self.snmpProxy.snmpConnInfo != self.snmpConnInfo):
            self.snmpProxy = self.snmpConnInfo.createSession()
            self.snmpProxy.open()

    def _close(self):
        """
        Close down the connection to the remote device
        """
        if self.snmpProxy:
            self.snmpProxy.close()
        self.snmpProxy = None
        

    def _showProcessList(self, procs):
        """
        Display the processes in a sane manner.

        @parameter procs: list of (pid, (name, args))
        @type procs: list of tuples
        """
        device_name = self._devId
        proc_list = [ '%s %s %s' % (pid, name, args) for pid, (name, args) \
                         in sorted(procs)]
        proc_list.append('')
        log.info("#===== Processes on %s:\n%s", device_name, '\n'.join(proc_list))

    def _clearSnmpError(self, message):
        """
        Send an event to clear other events.

        @parameter name: device for which the event applies
        @type name: string
        @parameter message: clear text
        @type message: string
        """
        self._eventService.sendEvent(self.statusEvent,
                                     eventClass=Status_Snmp,
                                     component="process",
                                     device=self._devId,
                                     summary=message,
                                     agent='zenprocess',
                                     severity=Event.Clear)

    def _save(self, pidName, statName, value, rrdType, min='U'):
        """
        Save a value into an RRD file

        @param pidName: process id of the monitored process
        @type pidName: string
        @param statName: metric name
        @type statName: string
        @param value: data to be stored
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        """
        deviceName = self._devId
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
        try:
            self._dataService.writeRRD(path, value, rrdType, min=min)
        except Exception, ex:
            summary= "Unable to save data for process-monitor RRD %s" % \
                              path
            log.critical( summary )

            message= "Data was value= %s, type=%s" % \
                     ( value, rrdType )
            log.critical( message )
            log.exception( ex )

            import traceback
            trace_info= traceback.format_exc()

            self._eventService.sendEvent(dict(
                dedupid="%s|%s" % (self._preferences.options.monitor, 
                                   'RRD write failure'),
                severity=Event.Critical,
                device=self._preferences.options.monitor,
                eventClass=Status_Perf,
                component="RRD",
                pidName=pidName,
                statName=statName,
                path=path,
                message=message,
                traceback=trace_info,
                summary=summary))

def mapResultsToDicts(showrawtables, results):
    """
    Parse the process tables and reconstruct the list of processes
    that are on the device.

    @parameter results: results of SNMP table gets ie (OID + pid, value)
    @type results: dictionary of dictionaries
    @return: maps relating names and pids to each other
    @rtype: dictionary, list of tuples
    """
    def extract(dictionary, oid, value):
        """
        Helper function to extract SNMP table data.
        """
        pid = int(oid.split('.')[-1])
        dictionary[pid] = value

    names, paths, args = {}, {}, {}
    if showrawtables:
        log.info("NAMETABLE = %r", results[NAMETABLE])
    for row in results[NAMETABLE].items():
        extract(names, *row)

    if showrawtables:
        log.info("PATHTABLE = %r", results[PATHTABLE])
    for row in results[PATHTABLE].items():
        extract(paths, *row)

    if showrawtables:
        log.info("ARGSTABLE = %r", results[ARGSTABLE])
    for row in results[ARGSTABLE].items():
        extract(args,  *row)

    procs = []
    for pid, name in names.items():
        path = paths.get(pid, '')
        if path and path.find('\\') == -1:
            name = path
        arg = args.get(pid, '')
        procs.append( (pid, (name, arg) ) )

    return args, procs

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

# Collector Daemon Main entry point
#
if __name__ == '__main__':
    myPreferences = ZenProcessPreferences()

    myTaskFactory = SimpleTaskFactory(ZenProcessTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
