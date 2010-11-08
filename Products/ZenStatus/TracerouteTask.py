###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """TracerouteTask

Determines the route to an IP addresses using TTLs (eg traceroute).

Invoke this file with the list of devices to traceroute to test by hand.

TracerouteTask.py host1 host2

"""

import time
import logging
log = logging.getLogger("zen.tracerouteTask")

import Globals
import zope.interface
import zope.component

from twisted.internet import defer, error

from Products.ZenCollector.interfaces import IScheduledTask,\
                                             IStatisticsService
from Products.ZenCollector.tasks import TaskStates
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenRRD.zencommand import Cmd, ProcessRunner, TimeoutError

MAX_TRACEROUTES = 10


class TracerouteTask(ObservableMixin):
    zope.interface.implements(IScheduledTask)

    STATE_TOPOLOGY_COLLECTION = 'TOPOLOGY_COLLECTION'
    STATE_TOPOLOGY_PROCESS  = 'TOPOLOGY_PROCESS_RESULTS'
    STATE_TOPOLOGY_UPDATE  = 'TOPOLOGY_UPDATE'

    def __init__(self,
                 taskName,
                 configId=None,
                 scheduleIntervalSeconds=60,
                 taskConfig=None,
                 daemonRef=None):
        """
        @param deviceId: the Zenoss deviceId to watch
        @type deviceId: string
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        @param daemonRef: a reference to the daemon
        """
        super(TracerouteTask, self).__init__()

        # Needed for interface
        self.name = taskName
        self.configId = configId if configId else taskName
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._preferences = taskConfig

        if daemonRef is None:
            raise TypeError("daemonRef cannot be None")
        self._daemon = daemonRef
        self._notModeled = self._daemon.network.notModeled
        self._traceTimedOut = self._daemon.network.traceTimedOut
        self._errorDevices = []

        # add our collector's custom statistics
        self._statService = zope.component.queryUtility(IStatisticsService)
        self._statService.addStatistic("traceroute_time", "GAUGE")

        self._modeledCount = 0
        self._failedModeledCount = 0

        self._maxTraceroutes = MAX_TRACEROUTES

        self._lastErrorMsg = ''

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        # Decode the exception
        if isinstance(reason.value, error.TimeoutError):
            msg = '%s second timeout connecting to device %s' % (
                      'timeout', self._devId)
            # Indicate that we've handled the error by
            # not returning a result
            reason = None

        else:
            msg = reason.getErrorMessage()
            if not msg: # Sometimes we get blank error messages
                msg = reason.__class__
            msg = '%s %s' % (self._devId, msg)

            # Leave 'reason' alone to generate a traceback

        if self._lastErrorMsg != msg:
            self._lastErrorMsg = msg
            if msg:
                log.error(msg)

        return reason

    def doTask(self):
        """
        Traceroute from the collector to the endpoint nodes,
        with chunking.

        @return: A task to traceroute devices
        @rtype: Twisted deferred object
        """
        self._daemon.network.saveTopology()
        deferredCmds = []
        devices = self._chooseDevicesToTrace()
        if not devices:
            return defer.succeed("No devices to trace at this time.")

        log.debug("Devices to trace: %s", devices)
        for devIp in devices:
            d = defer.maybeDeferred(self._modelRoute, devIp)
            deferredCmds.append(d)

        dl = defer.DeferredList(deferredCmds, consumeErrors=True)
        dl.addCallback(self._parseResults)
        dl.addCallback(self._processResults)
        return dl

    def cleanup(self):
        pass

    def _chooseDevicesToTrace(self):
        """
        Select the devices to traceroute
        """
        # Get the first chunkSize or fewer devices
        chunkSize = self._preferences.options.tracechunk
        traceDevices = self._daemon.network.disconnectedNodes()[:chunkSize]
        if not traceDevices:
            traceDevices = self._reTraceDevices(chunkSize)
        return traceDevices

    def _reTraceDevices(self, chunkSize):
        """
        Re-traceroute devices based on reasonable criteria.
        """
        traceDevices = self._errorDevices[:chunkSize]
        self._errorDevices = self._errorDevices[chunkSize:]
        if not traceDevices:
            pass
            # TODO: do something useful here (eg choose devices at random?)
        return traceDevices

    def _modelRoute(self, ip):
        """
        Given an IP address, perform a traceroute to determine (from the
        physical network devices) the underlying route to the IP from
        this collector device.

        @parameter ip: IP address of the device to search
        @type ip: string
        @returns: a deferred to actually do the modeling
        @rtype: deferred task
        """
        self.state = TracerouteTask.STATE_TOPOLOGY_COLLECTION
        # TODO: use a Python-level library rather than spawning a process
        cmd = Cmd()
        cmd.ds = "TRACEROUTE"
        cmd.ip = ip
        cmd.command = "traceroute -n %s" % ip
        cmd.name = cmd.command
        class DevProxy(object):
            zCommandCommandTimeout = self._preferences.options.tracetimeoutseconds
        cmd.deviceConfig = DevProxy()

        runner = ProcessRunner()
        d = runner.start(cmd)
        cmd.lastStart = time.time()
        d.addBoth(cmd.processCompleted)
        return d

    def _parseResults(self, resultList):
        """
        Take the raw results of the traceroute requests and format for
        updates to the topology.
        Note that just because a device cannot be traceroute'd does
        *NOT* mean that it is down.
        """
        self.state = TracerouteTask.STATE_TOPOLOGY_PROCESS
        newResultList = []
        for success, command in resultList:
            if success:
                self._modeledCount += 1
                result = self._parseResult(command)
                newResultList.append((success, result))
                self._updateStatistics(command)
            else:
                self._failedModeledCount += 1

                reason = command
                command, = reason.value.args
                self._errorDevices.append(command.ip)
                if isinstance(reason.value, TimeoutError):
                    msg = "Traceroute of %s timed out" % command.ip
                    log.debug(msg)
                    self._traceTimedOut.add(command.ip)
                else:
                    log.warn(reason.command.getTraceback())
        return newResultList

    def _parseResult(self, command):
        # Discard the first line of output
        output = command.result.output.split('\n')[1:]
        #  1  10.175.211.10  0.228 ms  0.146 ms  0.131 ms
        route = []
        for line in output:
            data = line.split()
            if not data:
                continue
            gw = data[1]
            route.append(gw) 

        # Note: sometimes we can't determine the route
        if not route or route[-1] != command.ip:
            route.append(command.ip)
        log.debug("Route: %s", route)
        return route

    def _updateStatistics(self, command):
        """
        Track our traceroute statistics
        """
        stat = self._statService.getStatistic("traceroute_time")
        stat.value = command.lastStop - command.lastStart

    def _processResults(self, resultList):
        """
        Given the list of gateways, add any nodes and construct
        any edges required to add the device to the topology.
        """
        self.state = TracerouteTask.STATE_TOPOLOGY_UPDATE
        updates = 0
        for success, route in resultList:
            if success:
                if self._daemon.network.updateTopology(route):
                    updates += 1

        return "Updated %d routes." % updates

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        badDeviceCount = len(self._errorDevices)
        display = "%s modelSuccesses: %d modelFailures: %s errorDevices: %s\n" % (
            self.name, self._modeledCount, self._failedModeledCount,
            self._errorDevices if badDeviceCount < 10 else badDeviceCount)
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__=='__main__':
    from twisted.internet import reactor
    from Products.ZenCollector.daemon import CollectorDaemon
    from Products.ZenStatus.zenping import PingCollectionPreferences
    from Products.ZenStatus.NetworkModel import NetworkModel
    from Products.ZenCollector.interfaces import ICollector
    from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                            SimpleTaskSplitter

    # Evil hack to avoid daemon command-line parsing
    def postStartup():
        daemon = zope.component.getUtility(ICollector)
        daemon.network = NetworkModel()

    myPreferences = PingCollectionPreferences()
    myPreferences.postStartup = postStartup

    # Daemon setup
    myTaskFactory = SimpleTaskFactory(TracerouteTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)

    # Now run traceroutes on devices
    daemon.network.notModeled = set(daemon.args)
    task = TracerouteTask('traceroute', 'traceroute', 300,
                               daemon._prefs, daemon)
    daemon._scheduler.addTask(task, daemon._taskCompleteCallback, True)
    log.setLevel(logging.DEBUG)
    reactor.run()
