###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """ZenCommand

Run Command plugins periodically.

"""

import random
import time
from pprint import pformat
import logging
log = logging.getLogger("zen.zencommand")
import traceback
from copy import copy

from twisted.internet import reactor, defer, error
from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure

from twisted.spread import pb

import Globals
import zope.interface

from Products.ZenUtils.Utils import unused, getExitMessage, readable_time
from Products.DataCollector.SshClient import SshClient
from Products.ZenEvents.ZenEventClasses import Clear, Error, Cmd_Fail, Cmd_Ok
from Products.ZenRRD.CommandParser import ParsedResults

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SubConfigurationTaskSplitter,\
                                        TaskStates, \
                                        BaseTask
from Products.ZenCollector.pools import getPool
from Products.ZenEvents import Event
from Products.ZenUtils.Executor import TwistedExecutor

from Products.DataCollector import Plugins
unused(Plugins)

MAX_CONNECTIONS = 250
MAX_BACK_OFF_MINUTES = 20

# We retrieve our configuration data remotely via a Twisted PerspectiveBroker
# connection. To do so, we need to import the class that will be used by the
# configuration service to send the data over, i.e. DeviceProxy.
from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

COLLECTOR_NAME = "zencommand"
POOL_NAME = 'SshConfigs'

class SshPerformanceCollectionPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new SshPerformanceCollectionPreferences instance and 
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.CommandPerformanceConfig'

        # Provide a reasonable default for the max number of tasks
        self.maxTasks = 50

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        parser.add_option('--showrawresults',
                          dest='showrawresults',
                          action="store_true",
                          default=False,
                          help="Show the raw RRD values. For debugging purposes only.")

        parser.add_option('--maxbackoffminutes',
                          dest='maxbackoffminutes',
                          default=MAX_BACK_OFF_MINUTES,
                          help="When a device fails to respond, increase the time to" \
                               " check on the device until this limit.")

        parser.add_option('--showfullcommand',
                          dest='showfullcommand',
                          action="store_true",
                          default=False,
                          help="Display the entire command and command-line arguments, " \
                               " including any passwords.")

    def postStartup(self):
        pass


class SshPerCycletimeTaskSplitter(SubConfigurationTaskSplitter):
    subconfigName = 'datasources'

    def makeConfigKey(self, config, subconfig):
        return (config.id, subconfig.cycleTime, 'Remote' if subconfig.useSsh else 'Local')


class TimeoutError(Exception):
    """
    Error for a defered call taking too long to complete
    """
    def __init__(self, *args):
        Exception.__init__(self)
        self.args = args


def timeoutCommand(deferred, seconds, obj):
    "Cause an error on a deferred when it is taking too long to complete"

    def _timeout(deferred, obj):
        "took too long... call an errback"
        deferred.errback(Failure(TimeoutError(obj)))

    def _cb(arg, timer):
        "the command finished, possibly by timing out"
        if not timer.called:
            timer.cancel()
        return arg

    timer = reactor.callLater(seconds, _timeout, deferred, obj)
    deferred.mytimer = timer
    deferred.addBoth(_cb, timer)
    return deferred


class ProcessRunner(ProcessProtocol):
    """
    Provide deferred process execution for a *single* command
    """
    stopped = None
    exitCode = None
    output = ''
    stderr = ''

    def start(self, cmd):
        """
        Kick off the process: run it local
        """
        log.debug('Running %s', cmd.command.split()[0])

        self._cmd = cmd
        shell = '/bin/sh'
        self.cmdline = (shell, '-c', 'exec %s' % cmd.command)
        self.command = ' '.join(self.cmdline)

        reactor.spawnProcess(self, shell, self.cmdline, env=cmd.env)

        d = timeoutCommand(defer.Deferred(), cmd.deviceConfig.zCommandCommandTimeout, cmd)
        self.stopped = d
        self.stopped.addErrback(self.timeout)
        return d

    def timeout(self, value):
        """
        Kill a process if it takes too long
        """
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            log.debug("Command already exited: %s", self.command.split()[0])
        return value

    def outReceived(self, data):
        """
        Store up the output as it arrives from the process
        """
        self.output += data

    def errReceived(self, data):
        """
        Store up the output as it arrives from the process
        """
        self.stderr += data

    def processEnded(self, reason):
        """
        Notify the starter that their process is complete
        """
        self.exitCode = reason.value.exitCode
        if self.exitCode is not None:
            msg = """Datasource: %s Received exit code: %s Output:\n%r"""
            data = [self._cmd.ds, self.exitCode, self.output]
            if self.stderr:
                msg += "\nStandard Error:\n%r"
                data.append(self.stderr)
            log.debug(msg, *data)

        if self.stopped:
            d, self.stopped = self.stopped, None
            if not d.called:
                d.callback(self)


class MySshClient(SshClient):
    """
    Connection to SSH server at the remote device
    """
    def __init__(self, *args, **kw):
        SshClient.__init__(self, *args, **kw)
        self.defers = {}
        self._taskList = set()

    def addCommand(self, command):
        """
        Run a command against the server
        """
        d = defer.Deferred()
        self.defers[command] = d
        SshClient.addCommand(self, command)
        return d

    def addResult(self, command, data, code):
        """
        Forward the results of the command execution to the starter
        """
        # don't call the CollectorClient.addResult which adds the result to a
        # member variable for zenmodeler
        d = self.defers.pop(command, None)
        if d is None:
            log.error("Internal error where deferred object not in dictionary." \
                      " Command = '%s' Data = '%s' Code = '%s'",
                      command.split()[0], data, code)
        elif not d.called:
            d.callback((data, code))

    def check(self, ip, timeout=2):
        """
        Turn off blocking SshClient.test method
        """
        return True

    def clientFinished(self):
        """
        We don't need to track commands/results when they complete
        """
        SshClient.clientFinished(self)
        self.cmdmap = {}
        self._commands = []
        self.results = []

    def clientConnectionFailed(self, connector, reason):
        """
        If we didn't connect let the modeler know

        @param connector: connector associated with this failure
        @type connector: object
        @param reason: failure object
        @type reason: object
        """
        self.clientFinished()
        message= reason.getErrorMessage()
        for task in list(self._taskList):
            task.connectionFailed(message)


class SshOptions:
    loginTries=1
    searchPath=''
    existenceTest=None

    def __init__(self, username, password, loginTimeout, commandTimeout,
            keyPath, concurrentSessions):
        self.username = username
        self.password = password
        self.loginTimeout=loginTimeout
        self.commandTimeout=commandTimeout
        self.keyPath = keyPath
        self.concurrentSessions = concurrentSessions


class SshRunner(object):
    """
    Run a single command across a cached SSH connection
    """

    def __init__(self, connection):
        self._connection = connection
        self.exitCode = None
        self.output = None
        self.stderr = None

    def start(self, cmd):
        "Initiate a command on the remote device"
        self.defer = defer.Deferred(canceller=self._canceller)
        try:
            d = timeoutCommand(self._connection.addCommand(cmd.command),
                        self._connection.commandTimeout,
                        cmd)
        except Exception, ex:
            log.warning('Error starting command: %s', ex)
            return defer.fail(ex)
        d.addErrback(self.timeout)
        d.addBoth(self.processEnded)
        return d

    def _canceller(self, deferToCancel):
        if not deferToCancel.mytimer.called:
            deferToCancel.mytimer.cancel()
        return None

    def timeout(self, arg):
        "Deal with slow executing command/connection (close it)"
        # We could send a kill signal, but then we would need to track
        # the command channel to send it. Just close the connection.
        return arg

    def processEnded(self, value):
        "Deliver ourselves to the starter with the proper attributes"
        if isinstance(value, Failure):
            return value
        self.output, self.exitCode = value
        return self


class DataPointConfig(pb.Copyable, pb.RemoteCopy):
    id = ''
    component = ''
    rrdPath = ''
    rrdType = None
    rrdCreateCommand = ''
    rrdMin = None
    rrdMax = None
    
    def __init__(self):
        self.data = {}
    
    def __repr__(self):
        return pformat((self.data, self.id))
    
pb.setUnjellyableForClass(DataPointConfig, DataPointConfig)

class Cmd(pb.Copyable, pb.RemoteCopy):
    """
    Holds the config of every command to be run
    """
    device = ''
    command = None
    ds = ''
    useSsh = False
    cycleTime = None
    eventClass = None
    eventKey = None
    severity = 3
    lastStart = 0
    lastStop = 0
    result = None
    env = None

    def __init__(self):
        self.points = []

    def processCompleted(self, pr):
        """
        Return back the datasource with the ProcessRunner/SshRunner stored in
        the the 'result' attribute.
        """
        self.result = pr
        self.lastStop = time.time()

        # Check for a condition that could cause zencommand to stop cycling.
        #   http://dev.zenoss.org/trac/ticket/4936
        if self.lastStop < self.lastStart:
           log.debug('System clock went back?')
           self.lastStop = self.lastStart

        if isinstance(pr, Failure):
            return pr

        log.debug('Process %s stopped (%s), %.2f seconds elapsed',
                self.name,
                pr.exitCode,
                self.lastStop - self.lastStart)
        return self

    def getEventKey(self, point):
        # fetch datapoint name from filename path and add it to the event key
        return self.eventKey + '|' + point.rrdPath.split('/')[-1]

    def commandKey(self):
        "Provide a value that establishes the uniqueness of this command"
        return '%'.join(map(str, [self.useSsh, self.cycleTime,
                        self.severity, self.command]))
    def __str__(self):
        return ' '.join(map(str, [
                        self.ds,
                        'useSSH=%s' % self.useSsh,
                        self.cycleTime, 
                       ]))

pb.setUnjellyableForClass(Cmd, Cmd)


STATUS_EVENT = { 'eventClass' : Cmd_Fail,
                    'component' : 'command',
}

class SshPerformanceCollectionTask(BaseTask):
    """
    A task that performs periodic performance collection for devices providing
    data via SSH connections.
    """
    zope.interface.implements(IScheduledTask)

    STATE_CONNECTING = 'CONNECTING'
    STATE_FETCH_DATA = 'FETCH_DATA'
    STATE_PARSE_DATA = 'PARSING_DATA'
    STATE_STORE_PERF = 'STORE_PERF_DATA'

    def __init__(self,
                 taskName,
                 configId,
                 scheduleIntervalSeconds,
                 taskConfig):
        """
        @param taskName: the unique identifier for this task
        @type taskName: string
        @param configId: configuration to watch
        @type configId: string
        @param scheduleIntervalSeconds: the interval at which this task will be
               collected
        @type scheduleIntervalSeconds: int
        @param taskConfig: the configuration for this task
        """
        super(SshPerformanceCollectionTask, self).__init__(
                 taskName, configId,
                 scheduleIntervalSeconds, taskConfig
               )

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig

        self._devId = self._device.id
        self._manageIp = self._device.manageIp

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        self._preferences = zope.component.queryUtility(ICollectorPreferences,
                                                        COLLECTOR_NAME)
        self._lastErrorMsg = ''

        self._maxbackoffseconds = self._preferences.options.maxbackoffminutes * 60

        self._concurrentSessions = taskConfig.zSshConcurrentSessions
        self._executor = TwistedExecutor(self._concurrentSessions)
        self._useSsh = taskConfig.datasources[0].useSsh
        self._connection = None

        self._datasources = taskConfig.datasources
        self.pool = getPool('SSH Connections')
        self.executed = 0

    def __str__(self):
        return "COMMAND schedule Name: %s configId: %s Datasources: %d" % (
               self.name, self.configId, len(self._datasources))

    def cleanup(self):
        return self._close()

    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: A task to scan the OIDs on a device.
        @rtype: Twisted deferred object
        """
        # See if we need to connect first before doing any collection
        d = defer.maybeDeferred(self._connect)
        d.addCallbacks(self._connectCallback, self._failure)
        d.addCallback(self._fetchPerf)

        # Call _finished for both success and error scenarois
        d.addBoth(self._finished)

        # Wait until the Deferred actually completes
        return d

    def _connect(self):
        """
        If a local datasource executor, do nothing.

        If an SSH datasource executor, create a connection to object the remote device.
        Make a new SSH connection object if there isn't one available.  This doesn't
        actually connect to the device.
        """
        if not self._useSsh:
            return defer.succeed(None)

        connection = self.pool.get(self._devId, None)
        if connection is None:
            self.state = SshPerformanceCollectionTask.STATE_CONNECTING
            log.debug("Creating connection object to %s", self._devId)
            username = self._device.zCommandUsername
            password = self._device.zCommandPassword
            loginTimeout = self._device.zCommandLoginTimeout
            commandTimeout = self._device.zCommandCommandTimeout
            keypath = self._device.zKeyPath
            options = SshOptions(username, password,
                              loginTimeout, commandTimeout,
                              keypath, self._concurrentSessions)

            connection = MySshClient(self._devId, self._manageIp,
                                 self._device.zCommandPort, options=options)
            connection.sendEvent = self._eventService.sendEvent

            self.pool[self._devId] = connection

            # Opens SSH connection to device
            connection.run()

        self._connection = connection
        self._connection._taskList.add(self)
        return connection

    def _close(self):
        """
        If a local datasource executor, do nothing.

        If an SSH datasource executor, relinquish a connection to the remote device.
        """
        if self._connection:
            self._connection._taskList.discard(self)
            if len(self._connection._taskList) == 0:
                self._connection.channelClosed():
                if self._devId in self.pool[self._devId]:
                    del self.pool[self._devId]
            self._connection = None
            # Note: deleting the connection from the pool means more work,
            #   but it also means that we won't have weird synchronization bugs
            #   with changes from the device not taking effect.

    def connectionFailed(self, msg):
        """
        This method is called by the SSH client when the connection fails.

        @parameter msg: message indicating the cause of the problem
        @type msg: string
        """
        # Note: Raising an exception and then catching it doesn't work
        #       as it appears that the exception is discarded in PBDaemon.py
        self.state = TaskStates.STATE_PAUSED
        log.error("Pausing task %s as %s [%s] connection failure: %s",
                  self.name, self._devId, self._manageIp, msg)
        self._eventService.sendEvent(STATUS_EVENT,
                                     device=self._devId,
                                     summary=msg,
                                     component=COLLECTOR_NAME,
                                     severity=Event.Error)
        self._commandsToExecute.cancel()

    def _failure(self, reason):
        """
        Twisted errBack to log the exception for a single device.

        @parameter reason: explanation of the failure
        @type reason: Twisted error instance
        """
        # Decode the exception
        if isinstance(reason.value, TimeoutError):
            cmd, = reason.value.args
            msg = "Command timed out on device %s: %r" % (
                    self._devId, cmd.command.split()[0])
            log.warning(msg)
            ev = self._makeCmdEvent(cmd, cmd.severity, msg)
            self._eventService.sendEvent(ev)

            # Don't log a traceback by not returning a result
            reason = None

        elif isinstance(reason.value, defer.CancelledError):
            # The actual issue is logged by connectionFailed
            # Don't log a traceback by not returning a result
            msg = "Task %s paused due to connection error" % self.name
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

        if reason:
            self._eventService.sendEvent(STATUS_EVENT,
                                     device=self._devId,
                                     summary=msg,
                                     severity=Event.Error)

        if self._useSsh:
            self._delayNextCheck()

        return reason

    def _connectCallback(self, result):
        """
        Callback called after a successful connect to the remote device.
        """
        if self._useSsh:
            log.debug("Connected to %s [%s]", self._devId, self._manageIp)
        else:
            log.debug("Running command(s) locally")
        return result

    def _addDatasource(self, datasource):
        """
        Add a new instantiation of ProcessRunner or SshRunner
        for every datasource.
        """
        if self._preferences.options.showfullcommand:
            log.info("Datasource %s command: %s", datasource.name,
                     datasource.command)

        if self._useSsh:
            runner = SshRunner(self._connection)
        else:
            runner = ProcessRunner()

        d = runner.start(datasource)
        datasource.lastStart = time.time()
        d.addBoth(datasource.processCompleted)
        return d

    def _fetchPerf(self, ignored):
        """
        Get performance data for all the monitored components on a device

        @parameter ignored: required to keep Twisted's callback chain happy
        @type ignored: result of previous callback
        """
        self.state = SshPerformanceCollectionTask.STATE_FETCH_DATA

        # The keys are the datasource names, which are composed of the
        # template name and the datasource name.  This combination is unique.
        cacheableDS = {}

        # Bundle up the list of tasks
        deferredCmds = []
        for datasource in self._datasources:
             if datasource.name in cacheableDS:
                 cacheableDS[datasource.name].append(datasource)
                 continue
             cacheableDS[datasource.name] = []

             datasource.deviceConfig = self._device
             task = self._executor.submit(self._addDatasource, datasource)
             deferredCmds.append(task)

        # Run the tasks
        dl = defer.DeferredList(deferredCmds, consumeErrors=True)
        dl.addCallback(self._parseResults, cacheableDS)
        dl.addCallback(self._storeResults)
        dl.addCallback(self._updateStatus)
        dl.addErrback(self._failure)

        # Save the list in case we need to cancel the commands
        self._commandsToExecute = dl
        return dl

    def _parseResults(self, resultList, cacheableDS):
        """
        Interpret the results retrieved from the commands and pass on
        the datapoint values and events.

        @parameter resultList: results of running the commands in a DeferredList
        @type resultList: array of (boolean, datasource)
        @parameter cacheableDS: other datasources that can use the same results
        @type cacheableDS: dictionary of arrays of datasources
        """
        self.state = SshPerformanceCollectionTask.STATE_PARSE_DATA
        parseableResults = []
        for success, datasource in resultList:
            results = ParsedResults()
            if not success:
                # In this case, our datasource is actually a defer.Failure
                reason = datasource
                datasource, = reason.value.args
                msg = "Datasource %s command timed out" % (
                         datasource.name)
                ev = self._makeCmdEvent(datasource, msg)
                results.events.append(ev)

            else:
                # Re-use our results for any similar datasources
                cachedDsList = cacheableDS.get(datasource.name)
                if cachedDsList:
                    for ds in cachedDsList:
                        ds.result = copy(datasource.result)
                        results = ParsedResults()
                        self._processDatasourceResults(ds, results)
                        parseableResults.append( (ds, results) )
                    results = ParsedResults()

                self._processDatasourceResults(datasource, results)

            parseableResults.append( (datasource, results) )
        return parseableResults

    def _makeParser(self, datasource, eventList):
        """
        Create a parser object to process data

        @parameter datasource: datasource containg information
        @type datasource: Cmd object
        @parameter eventList: list of events
        @type eventList: list of dictionaries
        """
        parser = None
        try:
            parser = datasource.parser.create()
        except Exception, ex:
            msg = "Error loading parser %s" % datasource.parser
            log.exception("%s %s %s", self.name, datasource.name, msg)
            ev = self._makeCmdEvent(datasource, msg)
            ev['message'] = traceback.format_exc()
            eventList.append(ev)
        return parser

    def _processDatasourceResults(self, datasource, results):
        """
        Process a single datasource's results

        @parameter datasource: datasource containg information
        @type datasource: Cmd object
        @parameter results: empty results object
        @type results: ParsedResults object
        """
        if not datasource.result.output:
            msg = "No data returned for command"
            log.warn("%s %s %s", self.name, datasource.name, msg)
            ev = self._makeCmdEvent(datasource, msg)
            results.events.append(ev)
            return

        parser = self._makeParser(datasource, results.events)
        if not parser:
            return

        try:
            parser.preprocessResults(datasource, log)
            parser.processResults(datasource, results)
            if datasource.result.stderr:
                self._addStderrMsg(datasource.result.stderr,
                                               results.events)
        except Exception, ex:
            msg = "Error running parser %s" % datasource.parser
            log.exception("%s %s %s", self.name, datasource.name, msg)
            ev = self._makeCmdEvent(datasource, msg)
            ev['message'] = traceback.format_exc()
            ev['output'] = datasource.result.output
            results.events.append(ev)

    def _addStderrMsg(self, stderrMsg, eventList):
        """
        Add the stderr output to error events.

        @parameter stderrMsg: stderr output from the command
        @type stderrMsg: string
        @parameter eventList: list of events
        @type eventList: list of dictionaries
        """
        for event in eventList:
            if event['severity'] not in ('Clear', 'Info', 'Debug'):
                event['stderr'] = stderrMsg

    def _storeResults(self, resultList):
        """
        Store the values in RRD files

        @parameter resultList: results of running the commands
        @type resultList: array of (datasource, dictionary)
        """
        self.state = SshPerformanceCollectionTask.STATE_STORE_PERF
        for datasource, results in resultList:
            for dp, value in results.values:
                threshData = {
                    'eventKey': datasource.getEventKey(dp),
                    'component': dp.component,
                }
                self._dataService.writeRRD(
                                  dp.rrdPath,
                                  value,
                                  dp.rrdType,
                                  dp.rrdCreateCommand,
                                  datasource.cycleTime,
                                  dp.rrdMin,
                                  dp.rrdMax,
                                  threshData)

        return resultList

    def _updateStatus(self, resultList):
        """
        Send any accumulated events

        @parameter resultList: results of running the commands
        @type resultList: array of (datasource, dictionary)
        """
        for datasource, results in resultList:
            self._clearEvent(datasource, results.events)
            for ev in results.events:
                self._eventService.sendEvent(ev, device=self._devId)
        return resultList

    def _clearEvent(self, datasource, eventList):
        """
        Ensure that a CLEAR event is sent for any command that
        successfully completes.
        """
        # If the result is a Failure, no exitCode exists
        exitCode = getattr(datasource.result, 'exitCode', -1)
        if exitCode is None or exitCode != 0:
            return

        clearEvents = [ev for ev in eventList if ev['severity'] == Clear]
        if not clearEvents:
            msg = 'Datasource %s command completed successfully' % (
                    datasource.name)
            ev = self._makeCmdEvent(datasource, msg, severity=Clear)
            eventList.append(ev)

    def _makeCmdEvent(self, datasource, msg, severity=None):
        """
        Create an event using the info in the Cmd object.
        """
        severity = datasource.severity if severity is None else severity
        ev = dict(
                  device=self._devId,
                  component=datasource.component,
                  eventClass=datasource.eventClass,
                  eventKey=datasource.eventKey,
                  severity=severity,
                  summary=msg
        )
        return ev

    def _finished(self, result):
        """
        Callback activated when the task is complete

        @parameter result: results of the task
        @type result: deferred object
        """
        if not isinstance(result, Failure):
            self._returnToNormalSchedule()

        try:
            self._close()
        except Exception, ex:
            log.warn("Failed to close device %s: error %s" %
                     (self._devId, str(ex)))

        # Return the result so the framework can track success/failure
        return result

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = "%s useSSH: %s\n" % (
            self.name, self._useSsh)
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__ == '__main__':
    # Required for passing classes from zenhub to here
    from Products.ZenRRD.zencommand import Cmd, DataPointConfig

    myPreferences = SshPerformanceCollectionPreferences()
    myTaskFactory = SimpleTaskFactory(SshPerformanceCollectionTask)
    myTaskSplitter = SshPerCycletimeTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()

