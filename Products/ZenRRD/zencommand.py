##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, 2010, 2012,  all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """ZenCommand

Run Command plugins periodically.

"""

import time
from pprint import pformat
import logging
log = logging.getLogger("zen.zencommand")
import traceback
from copy import copy
from functools import partial

from twisted.internet import defer
from twisted.python.failure import Failure

from twisted.spread import pb

import Globals
import zope.interface

from Products.ZenUtils.Utils import unused, getExitMessage
from Products.DataCollector.SshClient import SshClient
from Products.ZenEvents.ZenEventClasses import Clear, Cmd_Fail
from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD import runner

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IScheduledTask
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SubConfigurationTaskSplitter,\
                                        TaskStates, \
                                        BaseTask
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


# The following classes were refactored into the runner module after the
# 4.2 release. ZenPacks were importing those classes from here, so they
# must be exported for backwards compatibility.
ProcessRunner = runner.ProcessRunner
ProcessRunner.start = ProcessRunner.send
SshRunner = runner.SshRunner
SshRunner.start = SshRunner.send
TimeoutError = runner.TimeoutError


COLLECTOR_NAME = "zencommand"


class SshPerformanceCollectionPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new SshPerformanceCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 20  # minutes
        self.cycleInterval = 5 * 60  # seconds

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
                          type='int',
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


class MySshClient(SshClient):
    """
    Connection to SSH server at the remote device
    """
    zope.interface.implements(runner.IClient)

    def __init__(self, *args, **kw):
        super(MySshClient, self).__init__(*args, **kw)

        self.connect_defer = None
        self.close_defer = None
        self.command_defers = {}

        self.description = '%s:*****@%s:%s' % (self.username,
                                               self.ip,
                                               self.port)
        self.tasks = set()
        self.is_expired = False     # TODO: placeholder; not implemented yet

    def run(self):
        d = self.connect_defer = defer.Deferred()
        self.close_defer = defer.Deferred()
        super(MySshClient, self).run()
        return d

    def serviceStarted(self, sshconn):
        super(MySshClient, self).serviceStarted(sshconn)
        self.connect_defer.callback(self)

    def addCommand(self, command):
        """
        Run a command against the server
        """
        d = self.command_defers[command] = defer.Deferred()
        super(MySshClient, self).addCommand(command)
        return d

    def addResult(self, command, data, code, stderr):
        """
        Forward the results of the command execution to the starter
        """
        # don't call the CollectorClient.addResult which adds the result to a
        # member variable for zenmodeler
        d = self.command_defers.pop(command, None)
        if d is None:
            log.error("Internal error where deferred object not in dictionary." \
                      " Command = '%s' Data = '%s' Code = '%s' Stderr = '%s'",
                      command.split()[0], data, code, stderr)
        elif not d.called:
            d.callback((data, code, stderr))

    def clientConnectionLost(self, connector, reason):
        # Connection was lost, but could be because we just closed it. Not
        # necessarily cause for concern.
        msg = "Connection %s lost" % self.description
        log.debug(msg)
        self.close_defer.callback(msg)

    def check(self, ip, timeout=2):
        """
        Turn off blocking SshClient.test method
        """
        return True

    def clientFinished(self):
        """
        We don't need to track commands/results when they complete
        """
        super(MySshClient, self).clientFinished()
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
        msg = reason.getErrorMessage()
        self.connect_defer.errback(msg)
        self.close_defer.errback(msg)

        self.clientFinished()


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
            self.cycleTime, ]))

pb.setUnjellyableForClass(Cmd, Cmd)


STATUS_EVENT = {
    'eventClass': Cmd_Fail,
    'component': 'command',
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
        super(SshPerformanceCollectionTask, self).__init__(taskName,
                                                           configId,
                                                           scheduleIntervalSeconds,
                                                           taskConfig)

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds

        # The taskConfig corresponds to a DeviceProxy
        self._device = taskConfig
        self._devId = taskConfig.id
        self._manageIp = taskConfig.manageIp
        self._datasources = taskConfig.datasources

        self._useSsh = taskConfig.datasources[0].useSsh
        client = MySshClient if self._useSsh else None
        self._runner = partial(runner.getRunner, taskConfig, client)
        self._connector = self._runner()

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        preferences = zope.component.queryUtility(ICollectorPreferences,
                                                  COLLECTOR_NAME)
        self._maxbackoffseconds = preferences.options.maxbackoffminutes * 60
        self._showfullcommand = preferences.options.showfullcommand

        self._executor = TwistedExecutor(taskConfig.zSshConcurrentSessions)

        self.executed = 0
        self._lastErrorMsg = ''

    def __str__(self):
        return "COMMAND schedule Name: %s configId: %s Datasources: %d" % (
               self.name, self.configId, len(self._datasources))

    def cleanup(self):
        self._connector.close()

    @defer.inlineCallbacks
    def doTask(self):
        """
        Contact to one device and return a deferred which gathers data from
        the device.

        @return: Deferred actions to run against a device configuration
        @rtype: Twisted deferred object
        """
        self.state = SshPerformanceCollectionTask.STATE_CONNECTING
        try:
            yield self._connector.connect(self)

            if self._useSsh:
                msg = "Connected to %s [%s]" % (self._devId, self._manageIp)
                self._eventService.sendEvent(STATUS_EVENT,
                                             device=self._devId,
                                             summary=msg,
                                             component=COLLECTOR_NAME,
                                             severity=Clear)
            yield self._fetchPerf()
        except Exception, e:
            self.state = TaskStates.STATE_PAUSED
            log.error("Pausing task %s as %s [%s] connection failure: %s",
                      self.name, self._devId, self._manageIp, e.message)
            self._eventService.sendEvent(STATUS_EVENT,
                                         device=self._devId,
                                         summary=e.message,
                                         component=COLLECTOR_NAME,
                                         severity=Event.Error)
            raise e
        else:
            self._returnToNormalSchedule()
        finally:
            try:
                self._connector.close()
            except Exception, ex:
                log.warn("Failed to close device %s: error %s" %
                         (self._devId, str(ex)))

    def _addDatasource(self, datasource):
        """
        Add a new instantiation of ProcessRunner or SshRunner
        for every datasource.
        """
        if self._showfullcommand:
            log.info("Datasource %s command: %s", datasource.name,
                     datasource.command)

        d = self._runner(self._connector.connection).send(datasource)
        datasource.lastStart = time.time()
        d.addBoth(datasource.processCompleted)
        return d

    @defer.inlineCallbacks
    def _fetchPerf(self, ignored=None):
        """
        Get performance data for all the monitored components on a device

        @parameter ignored: required to keep Twisted's callback chain happy
        @type ignored: result of previous callback
        """
        self.state = SshPerformanceCollectionTask.STATE_FETCH_DATA

        # The keys are the datasource commands, which are by definition unique
        # to the command run.
        cacheableDS = {}

        # Bundle up the list of tasks
        deferredCmds = []
        for datasource in self._datasources:
            datasource.deviceConfig = self._device
            if datasource.command in cacheableDS:
                cacheableDS[datasource.command].append(datasource)
            else:
                cacheableDS[datasource.command] = []
                task = self._executor.submit(self._addDatasource, datasource)
                deferredCmds.append(task)

        # Run the tasks
        resultList = yield defer.DeferredList(deferredCmds, consumeErrors=True)
        parsedResults = self._parseResults(resultList, cacheableDS)
        self._storeResults(parsedResults)

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
        results = []
        for success, datasource in resultList:
            parsedResults = ParsedResults()
            
            if not success:
                # In this case, our datasource is actually a defer.Failure
                reason = datasource
                datasource, = reason.value.args
                msg = "Datasource %s command timed out" % datasource.name
                event = self._makeCmdEvent(datasource, msg)
            else:
                # clear our timeout event
                msg = "Datasource %s command timed out" % datasource.name
                event = self._makeCmdEvent(datasource, msg, severity=Clear)
                # Re-use our results for any similar datasources
                cache = cacheableDS.get(datasource.command, [])
                for ds in cache:
                    ds.result = copy(datasource.result)
                    self._processDatasourceResults(ds, parsedResults)
                    results.append((ds, parsedResults))
                    parsedResults = ParsedResults()

                self._processDatasourceResults(datasource, parsedResults)
            parsedResults.events.append(event)
            results.append((datasource, parsedResults))
        return results

    def _processDatasourceResults(self, datasource, results):
        """
        Process a single datasource's results

        @parameter datasource: datasource containg information
        @type datasource: Cmd object
        @parameter results: empty results object
        @type results: ParsedResults object
        """
        exitCode = datasource.result.exitCode
        output = datasource.result.output.strip()
        stderr = datasource.result.stderr.strip()
        
        if exitCode == 0 and not output:
            msg = "No data returned for command"
            if self._showfullcommand:
                msg += ": %s" % datasource.command
            log.warn("%s %s %s", self.name, datasource.name, msg)

            event = self._makeCmdEvent(datasource, msg)
            if self._showfullcommand:
                event['command'] = datasource.command
            results.events.append(event)
        else:
            try:
                operation = "Creating Parser"
                parser = datasource.parser.create()

                operation = "Running Parser"
                parser.preprocessResults(datasource, log)
                parser.processResults(datasource, results)

                if not results.events and \
                        parser.createDefaultEventUsingExitCode:
                    # If there is no event, send one based on the exit code
                    if exitCode == 0:
                        msg = ""
                        severity = Clear
                    else:
                        msg = "Datasource: %s - Code: %s - Msg: %s" % (
                            datasource.name, exitCode, getExitMessage(exitCode)
                        )
                        severity = datasource.severity
                    event = self._makeCmdEvent(datasource, msg, severity)
                    results.events.append(event)
                if stderr:
                    # Add the stderr output to the error events
                    for event in results.events:
                        if event['severity'] not in ('Clear', 'Info', 'Debug'):
                            event['stderr'] = stderr
            except Exception:
                msg = "Error %s %s" % (operation, datasource.parser)
                log.exception(msg)
                event = self._makeCmdEvent(datasource, msg)
                event['message'] = traceback.format_exc()
                event['output'] = output
                results.events.append(event)

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
                self._dataService.writeMetric(dp.contextUUID,
                                              dp.dpName,
                                              value,
                                              dp.rrdType,
                                              dp.componentId,
                                              deviceuuid=dp.devuuid,
                                              min=dp.rrdMin,
                                              max=dp.rrdMax,
                                              threshEventData=threshData)

            eventList = results.events
            exitCode = getattr(datasource.result, 'exitCode', -1)
            output = None
            if not isinstance(datasource.result, Failure):
                output = datasource.result.output.strip()
            if exitCode == 0 and output:
                # Ensure a CLEAR event is sent for any command that
                # successfully completes
                clearEvents = next((event for event in eventList if event['severity'] == Clear), None)
                if not clearEvents:
                    msg = "Datasource %s command completed successfully" % (
                        datasource.name
                    )
                    event = self._makeCmdEvent(datasource, msg, severity=Clear)
                    eventList.append(event)

            # Send accumulated events
            for event in eventList:
                self._eventService.sendEvent(event, device=self._devId)

    def _makeCmdEvent(self, datasource, msg, severity=None):
        """
        Create an event using the info in the Cmd object.
        """
        return dict(
            device=self._devId,
            component=datasource.component,
            eventClass=datasource.eventClass,
            eventKey=datasource.eventKey,
            severity=severity if severity is not None else datasource.severity,
            summary=msg
        )

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
