##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """NmapPingTask

Pings a all devices in the current device list.
"""

import logging
log = logging.getLogger("zen.NmapPingTask")
import tempfile
import subprocess
import math
from twisted.internet import utils
from twisted.internet import task as twistedTask
from twisted.internet import defer
from twisted.internet import reactor
import os.path
from cStringIO import StringIO
import stat
from collections import defaultdict
from datetime import datetime, timedelta

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
from Products.ZenStatus.interfaces import IPingTaskFactory, IPingTaskCorrelator
from Products.ZenStatus import nmap

_NMAP_BINARY = zenPath("bin/nmap")


_CLEAR = 0
_CRITICAL = 5
_WARNING = 3

MAX_PARALLELISM = 150
DEFAULT_PARALLELISM = 10
MAX_NMAP_OVERHEAD = 0.5 # in seconds
MIN_PING_TIMEOUT = 0.1 # in seconds

# amount of IPs/events to process before giving time to the reactor
_SENDEVENT_YIELD_INTERVAL = 100  # should always be >= 1

# amount of time since last ping down before count is removed from dictionary
DOWN_COUNT_TIMEOUT_MINUTES = 15

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
        # introduce a small delay to can have a chance to load some config
        task.startDelay = 5
        daemon._scheduler.addTask(task)
        correlationBackend = daemon.options.correlationBackend
        task._correlate = component.getUtility(IPingTaskCorrelator, correlationBackend)

    def buildOptions(self, parser):
        super(NmapPingCollectionPreferences, self).buildOptions(parser)
        parser.add_option('--connected-ip-suppress',
            dest='connectedIps',
            default=False,
            action="store_true",
            help="Suppress ping downs using interfaces on a device whose IPs may not be monitored")

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
        self._cycleIntervalReasonable = True # assume interval is fine at startup
        self.collectorName = self._daemon._prefs.collectorName

        # maps task name to ping down count and time of last ping down
        self._down_counts = defaultdict(lambda: (0, None))

    def _detectCycleInterval(self):
        """
        Detect whether the Ping Cycle Time is too short.
        """
        cycleInterval = self._daemon._prefs.pingCycleInterval
        minCycleInterval = MIN_PING_TIMEOUT + MAX_NMAP_OVERHEAD
        newValue = (cycleInterval >= minCycleInterval)
        if self._cycleIntervalReasonable != newValue:
            self._cycleIntervalReasonable = newValue
            if self._cycleIntervalReasonable == False:
                raise nmap.ShortCycleIntervalError(cycleInterval)
        self._sendShortCycleInterval(cycleInterval)

    def _sendShortCycleInterval(self, cycleInterval):
        """
        Send/Clear event to show that ping cycle time is short/fine.
        """
        if self._cycleIntervalReasonable:
            msg = "ping cycle time (%.1f seconds) is fine" % cycleInterval
            severity = _CLEAR
        else:
            minimum = MIN_PING_TIMEOUT + MAX_NMAP_OVERHEAD
            msg = "ping cycle time (%.1f seconds) is too short (keep it under %.1f seconds)" % (cycleInterval, minimum)
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="cycle_interval",
            severity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

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
            severity=severity,
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
        resolution = None
        if self._nmapIsSuid:
            msg = "nmap is set SUID" 
            severity = _CLEAR
        else:
            msg = "nmap is NOT SUID: %s" % _NMAP_BINARY
            try:
               import socket
               cmd = subprocess.check_output('echo "chown root.`id -gn` $ZENHOME/bin/nmap && chmod u+s $ZENHOME/bin/nmap"', shell=True).strip()
               resolution = "Log on to %s and execute the following as root: %s" % (socket.getfqdn(), cmd)
            except Exception as ex:
               log.exception("There was an error generating a help message related to sudo nmap.")
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="nmap_suid",
            severity=severity,
            summary=msg,
        )
        if resolution:
            evt['resolution'] = resolution
        self._eventService.sendEvent(evt)

    def _correlationExecution(self, ex=None):
        """
        Send/Clear event to show that correlation is executed properly.
        """
        if ex is None:
            msg = "correlation executed correctly" 
            severity = _CLEAR
        else:
            msg = "correlation did not execute correctly: %s" % ex
            severity = _CRITICAL
        evt = dict(
            device=self.collectorName,
            eventClass=ZenEventClasses.Status_Ping,
            eventGroup='Ping',
            eventKey="correlation_execution",
            severity=severity,
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
            severity=severity,
            summary=msg,
        )
        self._eventService.sendEvent(evt)

    @defer.inlineCallbacks
    def _executeNmapCmd(self, inputFileFilename, traceroute=False, outputType='xml', num_devices=0):
        """
        Execute nmap and return its output.
        """
        args = []
        args.extend(["-iL", inputFileFilename])  # input file
        args.append("-sn")               # don't port scan the hosts
        args.append("-PE")               # use ICMP echo
        args.append("-n")                # don't resolve hosts internally
        args.append("--privileged")      # assume we can open raw socket
        args.append("--send-ip")         # don't allow ARP responses
        args.append("-T5")               # "insane" speed
        if self._daemon.options.dataLength > 0:
            args.extend(["--data-length", str(self._daemon.options.dataLength)])

        cycle_interval = self._daemon._prefs.pingCycleInterval
        ping_tries     = self._daemon._prefs.pingTries
        ping_timeout   = self._preferences.pingTimeOut

        # Make sure the cycle interval is not unreasonably short.
        self._detectCycleInterval()

        # Make sure the timeout fits within one cycle.
        if ping_timeout + MAX_NMAP_OVERHEAD > cycle_interval:
            ping_timeout = cycle_interval - MAX_NMAP_OVERHEAD

        # Give each host at least that much time to respond.
        args.extend(["--min-rtt-timeout", "%.1fs" % ping_timeout])

        # But not more, so we can be exact with our calculations.
        args.extend(["--max-rtt-timeout", "%.1fs" % ping_timeout])

        # Make sure we can safely complete the number of tries within one cycle.
        if (ping_tries * ping_timeout + MAX_NMAP_OVERHEAD > cycle_interval):
            ping_tries = int(math.floor((cycle_interval - MAX_NMAP_OVERHEAD) / ping_timeout))
        args.extend(["--max-retries", "%d" % (ping_tries - 1)])

        # Try to force nmap to go fast enough to finish within one cycle.
        min_rate = int(math.ceil(num_devices / (1.0 * cycle_interval / ping_tries)))
        args.extend(["--min-rate","%d" % min_rate])

        if num_devices > 0:
            min_parallelism = int(math.ceil(2 * num_devices * ping_timeout / cycle_interval))
            if min_parallelism > MAX_PARALLELISM:
                min_parallelism = MAX_PARALLELISM
            if min_parallelism > DEFAULT_PARALLELISM:
                args.extend(["--min-parallelism", "%d" % min_parallelism])
        

        if traceroute:
            args.append("--traceroute")
            # FYI, all bets are off as far as finishing within the cycle interval.

        if outputType == 'xml':
            args.extend(["-oX", '-']) # outputXML to stdout
        else:
            raise ValueError("Unsupported nmap output type: %s" % outputType)

        # execute nmap
        if log.isEnabledFor(logging.DEBUG):
            log.debug("executing nmap %s", " ".join(args))
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
            #self._detectNmapIsSuid()  # will clear nmap_suid
            yield self._batchPing()   # will clear nmap_execution

        except nmap.NmapNotFound:
            self._sendNmapMissing()
        except nmap.NmapNotSuid:
            self._sendNmapNotSuid()
        except nmap.ShortCycleIntervalError:
            self._sendShortCycleInterval(self.interval)
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

        #only increment if we have tasks to ping
        self._pings += 1
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
                if self._pings == 0 or (self._pings % tracerouteInterval) == 0:
                    doTraceroute = True # try to traceroute on next ping

            import time
            i = 0
            for attempt in range(0, self._daemon._prefs.pingTries):

                start = time.time()
                results = yield self._executeNmapCmd(tfile.name, doTraceroute, num_devices=len(ipTasks))
                elapsed = time.time() - start
                log.debug("Nmap execution took %f seconds", elapsed)

                # only do traceroute on the first ping attempt, if at all
                doTraceroute = False 

                # record the results!
                for taskName, ipTask in ipTasks.iteritems():
                    i += 1
                    ip = ipTask.config.ip
                    if ip in results:
                        result = results[ip]
                        ipTask.logPingResult(result)
                    else:
                        # received no result, log as down
                        ipTask.logPingResult(PingResult(ip, isUp=False))
                    # give time to reactor to send events if necessary
                    if i % _SENDEVENT_YIELD_INTERVAL:
                        yield twistedTask.deferLater(reactor, 0, lambda: None)

            self._cleanupDownCounts()
            dcs = self._down_counts
            delayCount = self._daemon.options.delayCount
            pingTimeOut = self._preferences.pingTimeOut
            for taskName, ipTask in ipTasks.iteritems():
                i += 1
                if ipTask.isUp:
                    if taskName in dcs:
                        del dcs[taskName]
                    log.debug("%s is up!", ipTask.config.ip)
                    ipTask.delayedIsUp = True
                    ipTask.sendPingUp()
                    averageRtt = ipTask.averageRtt()
                    if averageRtt is not None:
                        if averageRtt/1000.0 > pingTimeOut: #millisecs to secs
                            ipTask.sendPingDegraded(rtt=averageRtt)
                        else:
                            ipTask.clearPingDegraded(rtt=averageRtt)
                else:
                    dcs[taskName] = (dcs[taskName][0] + 1, datetime.now())
                    if dcs[taskName][0] > delayCount:
                        log.debug("%s is down, %r", ipTask.config.ip, ipTask.trace)
                        ipTask.delayedIsUp = False
                    else:
                        fmt = '{0} is down. {1} ping downs received. ' \
                              'Delaying events until more than {2} ping ' \
                              'downs are received.'
                        args = (ipTask.config.ip, dcs[taskName][0],
                                delayCount)
                        log.debug(fmt.format(*args))

                ipTask.storeResults()
                # give time to reactor to send events if necessary
                if i % _SENDEVENT_YIELD_INTERVAL:
                    yield twistedTask.deferLater(reactor, 0, lambda: None)

            try:
                yield defer.maybeDeferred(self._correlate, ipTasks)
            except Exception as ex:
                self._correlationExecution(ex)
                log.critical("There was a problem performing correlation: %s", ex)
            else:
                self._correlationExecution() # send clear
            self._nmapExecution()

    def _cleanupDownCounts(self):
        """Clear out old down counts so process memory utilization doesn't
        grow."""
        now = datetime.now()
        timeout = timedelta(minutes=DOWN_COUNT_TIMEOUT_MINUTES)
        for taskName, (down_count, last_time) in self._down_counts.iteritems():
            if now - last_time > timeout:
                del self._down_counts[taskName]

    def _correlate(self, ipTasks):
        raise Exception("_correlate is not implemented in %r", self.__class__)

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        return ''

