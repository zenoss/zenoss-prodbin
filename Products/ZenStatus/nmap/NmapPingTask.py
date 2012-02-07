###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """NmapPingTask

Pings a all devices in the current device list.
"""

import logging
log = logging.getLogger("zen.NmapPingTask")
import tempfile
from twisted.internet import utils
from twisted.internet import task as twistedTask
from twisted.internet import defer
from twisted.internet import reactor
import os.path
from cStringIO import StringIO
import stat

import Globals
from zope import interface
from zope import component
from Products import ZenCollector
from Products.ZenCollector.tasks import BaseTask, TaskStates
from Products.ZenCollector import interfaces
from Products.ZenCollector.tasks import SimpleTaskFactory
from Products.ZenUtils.Utils import zenPath
from Products.ZenEvents import ZenEventClasses 
from zenoss.protocols.protobufs import zep_pb2 as events

# imports from within ZenStatus
from Products.ZenStatus import PingTask
from Products.ZenStatus.ping.CmdPingTask import CmdPingTask
from PingResult import PingResult, parseNmapXmlToDict
from Products.ZenStatus.PingCollectionPreferences import PingCollectionPreferences
from Products.ZenStatus.interfaces import IPingTaskFactory
from Products.ZenStatus import nmap

_NMAP_BINARY = zenPath("bin/nmap")


_CLEAR = 0
_CRITICAL = 5
_WARNING = 3

# amount of IPs/events to process before giving time to the reactor
_SENDEVENT_YIELD_INTERVAL = 100  # should always be >= 1

# twisted.callLater has trouble with sys.maxint as call interval, 
# just use a big interval, 100 years
_NEVER_INTERVAL = 60 * 60 * 24 * 365 * 100

class NmapPingCollectionPreferences(PingCollectionPreferences):
    
    def postStartup(self):
        """
        Hook in to application startup and start background NmapPingTask.
        """
        daemon = component.getUtility(interfaces.ICollector)
        task = NmapPingTask (
            'NmapPingTask',
            'NmapPingTask',
            taskConfig=daemon._prefs
        )
        daemon._scheduler.addTask(task, now=True)

class NPingTaskFactory(object):
    """
    A Factory to create PingTasks that do not run. This allows NmapPingTask
    to use the created PingTasks as placeholders for configuration.
    """
    interface.implements(IPingTaskFactory)

    def __init__(self):
        self.reset()

    def build(self):
        # Task spliter will gurantee every task has exactly one monitoredIp
        if self.config.monitoredIps[0].ipVersion == 6:
            # nmap does not support IPV6 ping/traceroute, use CmdPing
            log.debug("Creating an IPv6 task: %s", self.config.monitoredIps[0].ip)
            task = CmdPingTask(
                self.name,
                self.configId,
                self.interval,
                self.config,
            )
        else:
            log.debug("Creating an IPv4 task: %s", self.config.monitoredIps[0].ip)
            task = PingTask(
                self.name,
                self.configId,
                self.interval,
                self.config,
            )
            # don't run the tasks, they are used for storing config
            task.pauseOnScheduled = True
            task.interval = _NEVER_INTERVAL
        return task

    def reset(self):
        self.name = None
        self.configId = None
        self.interval = None
        self.config = None    

class NmapPingTask(BaseTask):
    interface.implements(ZenCollector.interfaces.IScheduledTask)
    """
    NmapPingTask pings all PingTasks using using nmap.
    """

    def __init__(self,
                 taskName, configId,
                 scheduleIntervalSeconds=60,
                 taskConfig=None):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(NmapPingTask, self).__init__(
                 taskName, configId,
                 scheduleIntervalSeconds, taskConfig=None
              )

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        self._daemon = component.getUtility(ZenCollector.interfaces.ICollector)
        self._dataService = component.queryUtility(ZenCollector.interfaces.IDataService)
        self._eventService = component.queryUtility(ZenCollector.interfaces.IEventService)
        
        self._pings = 0
        self._nmapPresent = False    # assume nmap is not present at startup
        self._nmapIsSuid = False     # assume nmap is not SUID at startup
        self.collectorName = self._daemon._prefs.collectorName
        
        
    def _detectNmap(self):
        """
        Detect that nmap is present.
        """
        # if nmap has already been detected, do not detect it again
        if self._nmapPresent:
            return
        self._nmapPresent = os.path.exists(_NMAP_BINARY)
        
        if self._nmapPresent == False:
            raise nmap.NmapNotFound()
        self._sendNmapMissing()
        
    def _sendNmapMissing(self):
        """
        Send/Clear event to show that nmap is present/missing.
        """
        if self._nmapPresent:
            msg = "nmap was found" 
            severity = _CLEAR
        else:
            msg = "nmap was NOT found at %r " % _NMAP_BINARY
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="nmap_missing",
            eventseverity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    def _detectNmapIsSuid(self):
        """
        Detect that nmap is set SUID
        """
        if self._nmapPresent and self._nmapIsSuid == False:
            # get attributes for nmap binary
            attribs = os.stat(_NMAP_BINARY)
            # find out if it is SUID and owned by root
            self._nmapIsSuid = (attribs.st_uid == 0) and (attribs.st_mode & stat.S_ISUID)
            if self._nmapIsSuid is False:
                raise nmap.NmapNotSuid()
        self._sendNmapNotSuid()  # send a clear

    def _sendNmapNotSuid(self):
        """
        Send/Clear event to show that nmap is set SUID.
        """
        if self._nmapIsSuid:
            msg = "nmap is set SUID" 
            severity = _CLEAR
        else:
            msg = "nmap is NOT SUID: %s" % _NMAP_BINARY
            severity = _WARNING
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="nmap_suid",
            eventseverity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    def _nmapExecution(self, ex=None):
        """
        Send/Clear event to show that nmap is executed properly.
        """
        if ex is None:
            msg = "nmap executed correctly" 
            severity = _CLEAR
        else:
            msg = "nmap did not execute correctly: %s" % ex
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="nmap_execution",
            eventseverity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    @defer.inlineCallbacks
    def _executeNmapCmd(self, inputFileFilename, traceroute=False, outputType='xml'):
        """
        Execute nmap and return it's output.
        """
        args = []
        args.extend(["-iL", inputFileFilename])  # input file
        args.append("-sn")               # don't port scan the hosts
        args.append("-PE")               # use ICMP echo 
        args.append("-n")                # don't resolve hosts internally
        args.append("--privileged")      # assume we can open raw socket
        args.append("--send-ip")         # don't allow ARP responses
        
        # give up on a host after spending too much time on it
        args.extend(["--initial-rtt-timeout", "%.1fs" % self._preferences.pingTimeOut])
        args.extend(["--min-rtt-timeout", "%.1fs" % self._preferences.pingTimeOut])
        
        if traceroute:
            args.append("--traceroute")
        
        if outputType == 'xml':
            args.extend(["-oX", '-']) # outputXML to stdout
        else:
            raise ValueError("Unsupported nmap output type: %s" % outputType)

        # execute nmap
        out, err, exitCode = yield utils.getProcessOutputAndValue(
            _NMAP_BINARY, args)

        if exitCode != 0:
            input = open(inputFileFilename).read()
            log.debug("input file: %s", input)
            log.debug("stdout: %s", out)
            log.debug("stderr: %s", err)
            raise nmap.NmapExecutionError(
                exitCode=exitCode, stdout=out, stderr=err, args=args)

        try:
            nmapResults = parseNmapXmlToDict(StringIO(out))
            defer.returnValue(nmapResults)
        except Exception as e:
            input = open(inputFileFilename).read()
            log.debug("input file: %s", input)
            log.debug("stdout: %s", out)
            log.debug("stderr: %s", err)
            log.exception(e)
            raise nmap.NmapExecutionError(
                exitCode=exitCode, stdout=out, stderr=err, args=args)

    @defer.inlineCallbacks
    def doTask(self):
        """
        BatchPingDevices !
        """
        log.debug('---- BatchPingDevices ----')
        
        if self.interval != self._daemon._prefs.pingCycleInterval:
            log.info("Changing ping interval from %r to %r ",
                self.interval,
                self._daemon._prefs.pingCycleInterval,
            )
            self.interval = self._daemon._prefs.pingCycleInterval
        
        try:
            self._detectNmap()        # will clear nmap_missing
            self._detectNmapIsSuid()  # will clear nmap_suid
            yield self._batchPing()   # will clear nmap_execution
            self._pings += 1
            
        except nmap.NmapNotFound:
            self._sendNmapMissing()
        except nmap.NmapNotSuid:
            self._sendNmapNotSuid()
        except nmap.NmapExecutionError as ex:
            self._nmapExecution(ex) 
            
        
    def _getPingTasks(self):
        """
        Iterate the daemons task list and find PingTask tasks that are IPV4.
        """
        tasks = self._daemon._scheduler._tasks
        pingTasks = {}
        for configName, task in tasks.iteritems():
            if isinstance(task.task, PingTask):
                if task.task.config.ipVersion == 4:
                    pingTasks[configName] = task.task
        return pingTasks

    @defer.inlineCallbacks
    def _batchPing(self):
        """
        Find the IPs, ping/traceroute, parse, correlate, and send events.
        """
        # find all devices to Ping
        ipTasks = self._getPingTasks()
        if len(ipTasks) == 0:
            log.debug("No ips to ping!")
            raise StopIteration() # exit this generator

        with tempfile.NamedTemporaryFile(prefix='zenping_nmap_') as tfile:
            ips = []
            for taskName, ipTask in ipTasks.iteritems():
                ips.append(ipTask.config.ip)
                ipTask.resetPingResult() # clear out previous run's results
            ips.sort()
            for ip in ips:
                tfile.write("%s\n" % ip)
            tfile.flush()

            # ping up to self._preferences.pingTries
            tracerouteInterval = self._daemon.options.tracerouteInterval
            
            # determine if traceroute needs to run
            doTraceroute = False
            if tracerouteInterval > 0:
                if self._pings == 0 or (tracerouteInterval % self._pings) == 0:
                    doTraceroute = True # try to traceroute on next ping

            for attempt in range(0, self._daemon._prefs.pingTries):

                results = yield self._executeNmapCmd(tfile.name, doTraceroute)
                # only do traceroute on the first ping attempt, if at all
                doTraceroute = False 

                # record the results!
                for taskName, ipTask in ipTasks.iteritems():
                    ip = ipTask.config.ip
                    if ip in results:
                        result = results[ip]
                        ipTask.logPingResult(result)
                    else:
                        # received no result, log as down
                        ipTask.logPingResult(PingResult(ip, isUp=False))

            downTasks = {}
            i = 0
            for taskName, ipTask in ipTasks.iteritems():
                i += 1
                if ipTask.isUp:
                    log.debug("%s is up!", ipTask.config.ip)
                    ipTask.sendPingUp()
                    ipTask.storeResults()
                else:
                    log.debug("%s is down", ipTask.config.ip)
                    downTasks[ipTask.config.ip] = ipTask
                    ipTask.storeResults()

                # give time to reactor to send events if necessary
                if i % _SENDEVENT_YIELD_INTERVAL:
                    yield twistedTask.deferLater(reactor, 0, lambda: None)
            
            yield self._correlate(downTasks)
            self._nmapExecution()

    @defer.inlineCallbacks
    def _correlate(self, downTasks):
        """
        Correlate ping down events.
        
        This simple correlator will take a list of PingTasks that are in the
        down state. It loops through the list and the last known trace route
        for each of the ip's. For every hop in the traceroute (starting from the
        collector to the ip in question), the hop's ip is searched for in
        downTasks. If it's found, then this collector was also monitoring the
        source of the problem.
        
        Note: this does not take in to account multiple routes to the ip in
        question. It uses only the last known traceroute as given by nmap which
        will not have routing loops and hosts that block icmp.
        """
        
        # for every down ipTask
        i = 0
        for currentIp, ipTask in downTasks.iteritems():
            i += 1
            # walk the hops in the traceroute
            for hop in ipTask.trace:
                # if a hop.ip alog the traceroute is in our list of down ips
                # and that hop.ip is not the currentIp then
                if hop.ip in downTasks and hop.ip != currentIp:
                    # we found our root cause!
                    rootCause = downTasks[hop.ip]
                    ipTask.sendPingDown(rootCause=rootCause)
                    break
            else:
                # no root cause found
                ipTask.sendPingDown()

            # give time to reactor to send events if necessary
            if i % _SENDEVENT_YIELD_INTERVAL:
                yield twistedTask.deferLater(reactor, 0, lambda: None, )

        # TODO: we could go a step further and ping all the ips along the last good
        # traceroute to give some insight as to where the problem may lie

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        return ''
