###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """ZenCommand

Run Command plugins periodically.

"""

import time
from pprint import pformat
import logging
log = logging.getLogger("zen.zencommand")
from sets import Set

from twisted.internet import reactor, defer, error
from twisted.internet.protocol import ProcessProtocol
from twisted.python import failure
from twisted.spread import pb

import Globals
from Products.ZenUtils.Driver import drive, driveLater

from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.DataCollector.SshClient import SshClient

from Products.ZenRRD.CommandParser import getParser, ParsedResults

MAX_CONNECTIONS = 256



class TimeoutError(Exception):
    """
    Error for a defered call taking too long to complete
    """

    def __init__(self, *args):
        Exception.__init__(self)
        self.args = args


def Timeout(deferred, seconds, obj):
    "Cause an error on a deferred when it is taking too long to complete"

    def _timeout(deferred, obj):
        "took too long... call an errback"
        deferred.errback(failure.Failure(TimeoutError(obj)))


    def _cb(arg, timer):
        "the command finished, possibly by timing out"
        if not timer.called:
            timer.cancel()
        return arg


    timer = reactor.callLater(seconds, _timeout, deferred, obj)
    deferred.addBoth(_cb, timer)
    return deferred


class ProcessRunner(ProcessProtocol):
    """
    Provide deferred process execution
    """
    stopped = None
    exitCode = None
    output = ''

    def start(self, cmd):
        "Kick off the process: run it local"
        log.debug('running %r' % cmd.command)

        shell = '/bin/sh'
        self.cmdline = (shell, '-c', 'exec %s' % cmd.command)
        self.command = ' '.join(self.cmdline)
        log.debug('cmd line: %r' % self.command)
        reactor.spawnProcess(self, shell, self.cmdline, env=None)

        d = Timeout(defer.Deferred(), cmd.deviceConfig.commandTimeout, cmd)
        self.stopped = d
        self.stopped.addErrback(self.timeout)
        return d

    def timeout(self, value):
        "Kill a process if it takes too long"
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            log.debug("Command already exited: %s" % self.command)
        return value


    def outReceived(self, data):
        "Store up the output as it arrives from the process"
        self.output += data


    def processEnded(self, reason):
        "notify the starter that their process is complete"
        self.exitCode = reason.value.exitCode
        log.debug('Received exit code: %s' % self.exitCode)
        log.debug('Command: %r' % self.command)
        log.debug('Output: %r' % self.output)
        
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

    def addCommand(self, command):
        "Run a command against the server"
        d = defer.Deferred()
        self.defers[command] = d
        SshClient.addCommand(self, command)
        return d


    def addResult(self, command, data, code):
        "Forward the results of the command execution to the starter"
        SshClient.addResult(self, command, data, code)
        d = self.defers.pop(command)
        if not d.called:
            d.callback((data, code))


    def check(self, ip, timeout=2):
        "Turn off blocking SshClient.test method"
        return True


    def clientFinished(self):
        "We don't need to track commands/results when they complete"
        SshClient.clientFinished(self)
        self.commands = []
        self.results = []


class SshPool:
    """
    Cache all the Ssh connections so they can be managed
    """

    def __init__(self):
        self.pool = {}


    def get(self, cmd):
        "Make a new SSH connection if there isn't one available"
        dc = cmd.deviceConfig
        result = self.pool.get(dc.device, None)
        if result is None:
            log.debug("Creating connection to %s", dc.device)
            options = Options(dc.username, dc.password,
                              dc.loginTimeout, dc.commandTimeout,
                              dc.keyPath)
            # New param KeyPath
            result = MySshClient(dc.device, dc.ipAddress, dc.port,
                                 options=options)
            result.run()
            self.pool[dc.device] = result
        return result


    def _close(self, device):
        "close the SSH connection to a device, if it exists"
        c = self.pool.get(device, None)
        if c:
            log.debug("Closing connection to %s", device)
            if c.transport:
                c.transport.loseConnection()
            del self.pool[device]

        
    def close(self, cmd):
        "symetric close that matches get() method"
        self._close(cmd.deviceConfig.device)


    def trimConnections(self, schedule):
        "reduce the number of connections using the schedule for guidance"
        # compute device list in order of next use
        devices = []
        for c in schedule:
            device = c.deviceConfig.device
            if device not in devices:
                devices.append(device)
        # close as many devices as needed
        while devices and len(self.pool) > MAX_CONNECTIONS:
            self._close(devices.pop())
            

class SshRunner:
    """
    Run a single command across a cached SSH connection
    """
    exitCode = None
    output = None

    def __init__(self, pool):
        self.pool = pool


    def start(self, cmd):
        "Initiate a command on the remote device"
        self.defer = defer.Deferred()
        c = self.pool.get(cmd)
        try:
            d = Timeout(c.addCommand(cmd.command),
                        cmd.deviceConfig.commandTimeout,
                        cmd)
        except Exception, ex:
            log.warning('Error starting command: %s', ex)
            self.pool.close(cmd)
            return defer.fail(ex)
        d.addErrback(self.timeout)
        d.addBoth(self.processEnded)
        return d


    def timeout(self, arg):
        "Deal with slow executing command/connection (close it)"
        cmd, = arg.value.args
        # we could send a kill signal, but then we would need to track
        # the command channel to send it to: just close the connection
        self.pool.close(cmd)
        return arg


    def processEnded(self, value):
        "Deliver ourselves to the starter with the proper attributes"
        if isinstance(value, failure.Failure):
            return value
        self.output, self.exitCode = value
        return self


class DeviceConfig(pb.Copyable, pb.RemoteCopy):
    lastChange = 0.
    device = ''
    ipAddress = ''
    port = 0
    username = ''
    password = ''
    loginTimeout = 0.
    commandTimeout = 0.
    keyPath = ''
pb.setUnjellyableForClass(DeviceConfig, DeviceConfig)


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
    command = None
    useSsh = False
    cycleTime = None
    eventClass = None
    eventKey = None
    severity = 3
    lastStart = 0
    lastStop = 0
    result = None


    def __init__(self):
        self.points = []

    def running(self):
        return self.lastStop < self.lastStart 


    def name(self):
        cmd, args = (self.command + ' ').split(' ', 1)
        cmd = cmd.split('/')[-1]
        return '%s %s' % (cmd, args)


    def nextRun(self):
        if self.running():
            return self.lastStart + self.cycleTime
        return self.lastStop + self.cycleTime


    def start(self, pool):
        if self.useSsh:
            pr = SshRunner(pool)
        else:
            pr = ProcessRunner()
        d = pr.start(self)
        self.lastStart = time.time()
        log.debug('Process %s started' % self.name())
        d.addBoth(self.processEnded)
        return d


    def processEnded(self, pr):
        self.result = pr
        self.lastStop = time.time()
        if not isinstance(pr, failure.Failure):
            log.debug('Process %s stopped (%s), %.2f seconds elapsed' % (
                self.name(),
                pr.exitCode,
                self.lastStop - self.lastStart))
            return self
        return pr


    def updateConfig(self, cfg, deviceConfig):
        self.deviceConfig = deviceConfig
        self.useSsh = cfg.useSsh
        self.cycleTime = max(cfg.cycleTime, 1)
        self.eventKey = cfg.eventKey
        self.eventClass = cfg.eventClass
        self.severity = cfg.severity
        self.command = str(cfg.command)
        self.points = cfg.points
        return self

    def getEventKey(self, point):
        # fetch datapoint name from filename path and add it to the event key
        return self.eventKey + '|' + point.rrdPath.split('/')[-1]

    def commandKey(self):
        "Provide a value that establishes the uniqueness of this command"
        return '%'.join(map(str, [self.useSsh, self.cycleTime,
                                  self.severity, self.command]))

pb.setUnjellyableForClass(Cmd, Cmd)

class Options:
    loginTries=1
    searchPath=''
    existenceTest=None

    def __init__(self, username, password, loginTimeout, commandTimeout, keyPath):
        self.username = username
        self.password = password
        self.loginTimeout=loginTimeout
        self.commandTimeout=commandTimeout
        self.keyPath = keyPath


def warnUsernameNotSet(device, sshCmd, sendEvent, suppressed):
    """
    Warn that the username is not set for device and the SSH command cannot be
    executed.
    """
    if device not in suppressed:
        summary = 'zCommandUsername is not set'
        log.warning(summary + ' for %s' % device)
        sendEvent(dict(device=device,
                       eventClass='/Cmd/Fail',
                       eventKey='zCommandUsername',
                       severity=4,
                       component='zencommand',
                       summary=summary))
    msg = 'username not configured for %s. skipping %s.'
    log.debug(msg % (device, sshCmd.command))


def updateCommands(config, currentDict, sendEvent):
    """
    Go through the Cmd objects in config.commands and update the config on the
    command with config. If currentDict has the command on it then use that
    one, otherwise use the command from config. If the device does not have a
    username set, then don't yield commands that use SSH.
    
    Parameters:
        
        config - one of the configurations that was returned by calling
        getDataSourceCommands on zenhub.
        
        currentDict - a dictionary that maps (device, command) to Cmd object
        for the commands currently on zencommand's schedule.
    """
    
    suppressed = [] # log warning and send event once per device 
    
    for cmd in config.commands:

        key = (config.device, cmd.command)
        
        if not config.username and cmd.useSsh:
            warnUsernameNotSet(config.device, cmd, sendEvent, suppressed)
            if config.device not in suppressed:
                suppressed.append(config.device)
            if key in currentDict:
                del currentDict[key]
            continue
            
        if key in currentDict: newCmd = currentDict.pop(key)
        else                       : newCmd = cmd
        
        yield newCmd.updateConfig(cmd, config)


class zencommand(RRDDaemon):
    """
    Daemon code to schedule commands and run them.
    """

    initialServices = RRDDaemon.initialServices + ['CommandConfig']

    def __init__(self):
        RRDDaemon.__init__(self, 'zencommand')
        self.schedule = []
        self.timeout = None
        self.pool = SshPool()
        self.executed = 0

    def remote_deleteDevice(self, doomed):
        self.log.debug("zenhub has asked us to delete device %s" % doomed)
        self.schedule = [c for c in self.schedule if c.deviceConfig.device != doomed]
            
    def remote_updateConfig(self, config):
        self.log.debug("Configuration update from zenhub")
        self.updateConfig([config], [config.device])

    def remote_updateDeviceList(self, devices):
        self.log.debug("zenhub sent updated device list %s" % devices)
        updated = []
        lastChanges = dict(devices)     # map device name to last change
        keep = []
        for cmd in self.schedule:
            if cmd.deviceConfig.device in lastChanges:
                if cmd.lastChange > lastChanges[cmd.device]:
                    updated.append(cmd.deviceConfig.device)
                keep.append(cmd)
            else:
                self.log.info("Removing all commands for %s", cmd.deviceConfig.device)
        self.schedule = keep
        if updated:
            self.log.info("Fetching the config for %s", updated)
            d = self.model().callRemote('getDataSourceCommands', devices)
            d.addCallback(self.updateConfig, updated)
            d.addErrback(self.error)

    def updateConfig(self, configs, expected):
        expected = Set(expected)
        current = {}
        for c in self.schedule:
            if c.deviceConfig.device in expected:
                current[c.deviceConfig.device,c.command] = c
        # keep all the commands we didn't ask for
        update = [c for c in self.schedule if c.deviceConfig.device not in expected]
        for cfg in configs:
            self.thresholds.updateForDevice(cfg.device, cfg.thresholds)
            if self.options.device and self.options.device != cfg.device:
                continue
            update.extend(updateCommands(cfg, current, self.sendEvent))
        for device, command in current.keys():
            self.log.info("Deleting command %s from %s", device, command)
        self.schedule = update
        self.processSchedule()

    def heartbeatCycle(self, *ignored):
        "There is no master 'cycle' to send the hearbeat"
        self.heartbeat()
        reactor.callLater(self.heartbeatTimeout/3, self.heartbeatCycle)
        events = []
        events += self.rrdStats.gauge('schedule',
                                      self.heartbeatTimeout,
                                      len(self.schedule))
        events += self.rrdStats.counter('commands',
                                        self.heartbeatTimeout,
                                        self.executed)
        events += self.rrdStats.counter('dataPoints',
                                        self.heartbeatTimeout,
                                        self.rrd.dataPoints)
        events += self.rrdStats.gauge('cyclePoints',
                                      self.heartbeatTimeout,
                                      self.rrd.endCycle())
        self.sendEvents(events)
        

    def processSchedule(self, *unused):
        """
        Run through the schedule and start anything that needs to be done.
        Set a timer if we have nothing to do.
        """
        if not self.options.cycle:
            for cmd in self.schedule:
                if cmd.running() or cmd.lastStart == 0:
                    break
            else:
                self.stop()
                return
        try:
            if self.timeout and not self.timeout.called:
                self.timeout.cancel()
                self.timeout = None
            def compare(x, y):
                return cmp(x.nextRun(), y.nextRun())
            self.schedule.sort(compare)
            self.pool.trimConnections(self.schedule)
            earliest = None
            running = 0
            now = time.time()
            for c in self.schedule:
                if c.running():
                    running += 1

            for c in self.schedule:
                if running >= self.options.parallel:
                    break
                if c.nextRun() <= now:
                    c.start(self.pool).addBoth(self.finished)
                    running += 1
                else:
                    earliest = c.nextRun() - now
                    break

            if earliest is not None:
                self.log.debug("Next command in %d seconds", int(earliest))
                self.timeout = reactor.callLater(max(1, earliest),
                                                 self.processSchedule)
        except Exception, ex:
            self.log.exception(ex)

            
    def finished(self, cmd):
        self.executed += 1
        if isinstance(cmd, failure.Failure):
            self.error(cmd)
        else:
            self.parseResults(cmd)
        self.processSchedule()


    def error(self, err):
        if isinstance(err.value, TimeoutError):
            cmd, = err.value.args
            dc = cmd.deviceConfig
            msg = "Command timed out on device %s: %r" % (dc.device, cmd.command)
            self.log.warning(msg)
            self.sendEvent(dict(device=dc.device,
                                component="zencommand",
                                eventClass=cmd.eventClass,
                                eventKey=cmd.eventKey,
                                severity=cmd.severity,
                                summary=msg))
        else:
            self.log.exception(err.value)

    def parseResults(self, cmd):
        """
        Process the results of our command-line, send events
        and check datapoints.

        @param cmd: command
        @type: cmd object
        """
        self.log.debug('The result of "%s" was "%r"', cmd.command, cmd.result.output)
        results = ParsedResults()
        try:
            parser = getParser(cmd.parser)
        except Exception, ex:
            self.log.exception("Error loading parser %s" % cmd.parser)
            import traceback
            self.sendEvent(dict(device=cmd.deviceConfig.device,
                           summary="Error loading parser %s" % cmd.parser,
                           component="zencommand",
                           message=traceback.format_exc(),
                           agent="zencommand",
                          ))
            return
        parser.processResults(cmd, results)

        for ev in results.events:
            self.sendEvent(ev, device=cmd.deviceConfig.device)

        for dp, value in results.values:
            self.log.debug("Storing %s = %s into %s" % (dp.id, value, dp.rrdPath))
            value = self.rrd.save(dp.rrdPath,
                                  value,
                                  dp.rrdType,
                                  dp.rrdCreateCommand,
                                  cmd.cycleTime,
                                  dp.rrdMin,
                                  dp.rrdMax)
            self.log.debug("RRD save result: %s" % value)
            for ev in self.thresholds.check(dp.rrdPath, time.time(), value):
                eventKey = cmd.getEventKey(dp)
                if 'eventKey' in ev:
                    ev['eventKey'] = '%s|%s' % (eventKey, ev['eventKey'])
                else:
                    ev['eventKey'] = eventKey
                ev['component'] = dp.component
                self.sendEvent(ev)

    def fetchConfig(self):
        def doFetchConfig(driver):
            try:
                now = time.time()
                
                yield self.model().callRemote('propertyItems')
                self.setPropertyItems(driver.next())

                yield self.model().callRemote('getDefaultRRDCreateCommand')
                createCommand = driver.next()

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
                yield self.model().callRemote('getDataSourceCommands',
                                              devices)
                if not devices:
                    devices = list(Set([c.deviceConfig.device
                                        for c in self.schedule]))
                self.updateConfig(driver.next(), devices)

                self.rrd = RRDUtil(createCommand, 60)

                self.sendEvents(
                    self.rrdStats.gauge('configTime',
                                        self.configCycleInterval * 60,
                                        time.time() - now))

            except Exception, ex:
                self.log.exception(ex)
                raise

        return drive(doFetchConfig)
            

    def start(self, driver):
        """
        Fetch the configuration and return a deferred for its completion.
        Also starts the config cycle
        """
        ex = None
        try:
            self.log.debug('Fetching configuration from zenhub')
            yield self.fetchConfig()
            driver.next()
            self.log.debug('Finished config fetch')
        except Exception, ex:
            self.log.exception(ex)
        driveLater(self.configCycleInterval * 60, self.start)
        if ex:
            raise ex

    def buildOptions(self):
        RRDDaemon.buildOptions(self)

        self.parser.add_option('--parallel', dest='parallel', 
                               default=10, type='int',
                               help="Number of devices to collect at one time")
        
    def connected(self):
        d = drive(self.start).addCallbacks(self.processSchedule, self.errorStop)
        if self.options.cycle:
            d.addCallback(self.heartbeatCycle)


if __name__ == '__main__':
    from Products.ZenRRD.zencommand import zencommand
    z = zencommand()
    z.run()
