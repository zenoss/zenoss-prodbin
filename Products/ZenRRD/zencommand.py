#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__=''' ZenCommand

Run Command pluggins periodically.

$Id$'''

__version__ = "$Revision$"[11:-2]

import time
import logging
log = logging.getLogger("zen.zencommand")

from twisted.internet import reactor, defer
from twisted.internet.protocol import ProcessProtocol
from twisted.python import failure

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenEvents import Event

from Products.ZenRRD.RRDDaemon import RRDDaemon, Threshold, ThresholdManager
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.DataCollector.SshClient import SshClient

from sets import Set

import re
# how to parse each value from a nagios command
NagParser = re.compile(r"""([^ =']+|'(.*)'+)=([-0-9.]+)([^;]*;?){0,5}""")
# how to parse each value from a cacti command
CacParser = re.compile(r"""([^ :']+|'(.*)'+):([-0-9.]+)""")

MAX_CONNECTIONS=50

class CommandConfig:
    def __init__(self, dictionary):
        d = dictionary.copy()
        d['self'] = self
        self.__dict__.update(dictionary)
    

class TimeoutError(Exception):
    "Error for a defered call taking too long to complete"

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
    "Provide deferred process execution"
    stopped = None
    exitCode = None
    output = ''

    def start(self, cmd):
        "Kick off the process: run it local"
        log.debug('running %r' % cmd.command)
        d = Timeout(defer.Deferred(), cmd.commandTimeout, cmd)
        self.stopped = d
        self.stopped.addErrback(self.timeout)
        reactor.spawnProcess(self, '/bin/sh',
                             ('/bin/sh', '-c', 'exec ' + cmd.command))
        return d

    def timeout(self, value):
        "Kill a process if it takes too long"
        self.transport.signalProcess('KILL')
        return value


    def outReceived(self, data):
        "Store up the output as it arrives from the process"
        self.output += data


    def processEnded(self, reason):
        "notify the starter that their process is complete"
        self.exitCode = reason.value.exitCode
        log.debug('Received exit code %s for: %r' % (self.exitCode, self.output))
        self.output = [s.strip() for s in self.output.split('\n')][0]
        if self.stopped:
            d, self.stopped = self.stopped, None
            if not d.called:
                d.callback(self)


class MySshClient(SshClient):
    "Connection to SSH server at the remote device"

    def __init__(self, *args, **kw):
        SshClient.__init__(self, *args, **kw)
        self.defers = []

    
    def addCommand(self, command):
        "Run a command against the server"
        d = defer.Deferred()
        self.defers.append(d)
        SshClient.addCommand(self, command)
        return d


    def addResult(self, command, data, code):
        "Forward the results of the command execution to the starter"
        SshClient.addResult(self, command, data, code)
        d = self.defers.pop(0)
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
    "Cache all the Ssh connections so they can be managed" 

    def __init__(self):
        self.pool = {}


    def get(self, cmd):
        "Make an ssh connection if there isn't one available"
        result = self.pool.get(cmd.device, None)
        if result is None:
            log.debug("Creating connection to %s", cmd.device)
            options = Options(cmd.username, cmd.password,
                              cmd.loginTimeout, cmd.commandTimeout)
            result = MySshClient(cmd.device, cmd.ipAddress, cmd.port,
                                 options=options)
            result.run()
            self.pool[cmd.device] = result
        return result


    def _close(self, device):
        "close the SSH connection to a device, if it exists"
        c = self.pool.get(device, None)
        if c:
            log.debug("Closing connection to %s", device)
            if c.connection and c.connection.transport:
                c.connection.transport.loseConnection()
            del self.pool[device]

        
    def close(self, cmd):
        "symetric close that matches get() method"
        self._close(cmd.device)


    def trimConnections(self, schedule):
        "reduce the number of connections using the schedule for guidance"
        # compute device list in order of next use
        devices = []
        for c in schedule:
            if c.device not in devices:
                devices.append(c.device)
        # close as many devices as needed
        while devices and len(self.pool) > MAX_CONNECTIONS:
            self._close(devices.pop())
            

class SshRunner:
    "Run a single command across a cached Ssh connection"
    exitCode = None
    output = None

    def __init__(self, pool):
        self.pool = pool


    def start(self, cmd):
        "Initiate a command on the remote device"
        self.defer = defer.Deferred()
        c = self.pool.get(cmd)
        d = Timeout(c.addCommand(cmd.command), cmd.commandTimeout, cmd)
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


class Cmd:
    "Holds the config of every command to be run"
    device = None
    ipAddress = None
    port = 22
    username = None
    password = None
    command = None
    useSsh = False
    cycleTime = None
    eventClass = None
    eventKey = None
    component = None
    severity = 3
    lastStart = 0
    lastStop = 0
    result = None


    def __init__(self):
        self.points = {}

    def running(self):
        return self.lastStop < self.lastStart 


    def name(self):
        cmd, args = (self.command + ' ').split(' ', 1)
        cmd = cmd.split('/')[-1]
        if len(args) > 10:
            return '%s %s...%s' % (cmd, args[:10], args[-10:])
        return '%s %s' % (cmd, args)


    def nextRun(self):
        if self.running():
            return self.lastStart
        return self.lastStop + self.cycleTime


    def start(self, pool):
        self.lastStart = time.time()
        if self.useSsh:
            pr = SshRunner(pool)
        else:
            pr = ProcessRunner()
        d = pr.start(self)
        log.debug('Process %s started' % self.name())
        d.addBoth(self.processEnded)
        return d


    def processEnded(self, pr):
        self.result = pr
        self.lastStop = time.time()
        if not isinstance(pr, failure.Failure):
            log.debug('Process %s stopped (%s), %f elapsed' % (
                self.name(),
                pr.exitCode,
                self.lastStop - self.lastStart))
            return self
        return pr


    def updateConfig(self, cfg):
        self.device = cfg.device
        self.ipAddress = cfg.ipAddress
        self.port = cfg.port
        self.username = cfg.username
        self.password = cfg.password
        self.loginTimeout = cfg.loginTimeout
        self.commandTimeout = cfg.commandTimeout
        self.useSsh = cfg.useSsh
        self.cycleTime = max(cfg.cycleTime, 1)
        self.eventKey = cfg.eventKey
        self.eventClass = cfg.eventClass
        self.component = cfg.component
        self.severity = cfg.severity
        self.command = cfg.command
        self.points, before = {}, self.points
        for p in cfg.points:
            index = p[0]
            threshs = p[-1]
            middle = p[1:-1]
            values = before.get(index, [ThresholdManager()])
            m = values[-1]
            m.update(threshs)
            self.points[index] = list(middle) + [m]

class Options:
    loginTries=1
    searchPath=''
    existenceTest=None

    def __init__(self, username, password, loginTimeout, commandTimeout):
        self.username = username
        self.password = password
        self.loginTimeout=loginTimeout
        self.commandTimeout=commandTimeout


class zencommand(RRDDaemon):
    properties = RRDDaemon.properties + ("configCycleInterval",)


    def __init__(self):
        RRDDaemon.__init__(self, 'zencommand')
        self.schedule = []
        self.timeout = None
        self.deviceIssues = Set()
        self.flushEvents()
        self.pool = SshPool()


    def flushEvents(self):
        self.sendEvents()
        reactor.callLater(1, self.flushEvents)


    def updateConfig(self, config):
        table = dict([((c.device,c.command), c) for c in self.schedule])

        for c in config:
            (device, ipAddress, port,
             username, password,
             loginTimeout, commandTimeout, commandPart) = c
            if self.options.device and self.options.device != device:
                continue
            for cmd in commandPart:
                (useSsh, cycleTime,
                 component, eventClass, eventKey, severity, command, points) = cmd
                obj = table.setdefault((device,command), Cmd())
                obj.updateConfig(CommandConfig(locals()))
        self.schedule = table.values()

    def heartbeatCycle(self, *ignored):
        "There is no master 'cycle' to send the hearbeat"
        self.heartbeat()
        reactor.callLater(self.heartBeatTimeout, self.heartbeatCycle)

    def processSchedule(self, *unused):
        """Run through the schedule and start anything that needs to be done.
        Set a timer if we have nothing to do.
        """
        if not self.options.cycle:
            for cmd in self.schedule:
                if cmd.running() or cmd.lastStart == 0:
                    break
            else:
                self._shutdown()
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
                elif c.nextRun() <= now:
                    c.start(self.pool).addBoth(self.finished)
                    running += 1
                else:
                    earliest = c.nextRun() - now
                    break
                if running >= self.options.parallel:
                    break
            if earliest is not None:
                log.debug("Next command in %f seconds", earliest)
                self.timeout = reactor.callLater(earliest,
                                                 self.processSchedule)
        except Exception, ex:
            log.exception(ex)

            
    def finished(self, cmd):
        if isinstance(cmd, failure.Failure):
            self.error(cmd)
        else:
            self.parseResults(cmd)
        self.processSchedule()


    def error(self, err):
        if isinstance(err.value, TimeoutError):
            cmd, = err.value.args
            log.error("Command timed out on device %s: %s",
                      cmd.device, cmd.command)
        else:
            log.exception(err.value)

    def parseResults(self, cmd):
        log.debug('The result of "%s" was "%s"', cmd.command, cmd.result.output)
        output = cmd.result.output
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        issueKey = cmd.device, cmd.eventClass, cmd.eventKey
        if output.find('|') >= 0:
            msg, values = output.split('|', 1)
        elif CacParser.search(output):
            msg, values = '', output
        else:
            msg, values = output, ''
        msg = msg.strip() or ('exit code: %d' % exitCode)
        if exitCode == 0:
            severity = 0
        elif exitCode == 2:
            severity = min(severity + 1, 5)
        if severity or issueKey in self.deviceIssues:
            self.sendThresholdEvent(device=cmd.device,
                                    summary=msg,
                                    severity=severity,
                                    message=msg,
                                    performanceData=values,
                                    eventKey=cmd.eventKey,
                                    eventClass=cmd.eventClass,
                                    component=cmd.component)
            self.deviceIssues.add(issueKey)
        if severity == 0:
            self.deviceIssues.discard(issueKey)

        for value in values.split(' '):
            if value.find('=') > 0:
                parts = NagParser.match(value)
            else:
                parts = CacParser.match(value)
            if not parts: continue
            label = parts.group(1).replace("''", "'")
            value = float(parts.group(3))
            if cmd.points.has_key(label):
                path, type, command, thresholds = cmd.points[label]
                log.debug("storing %s = %s in: %s" % (label, value, path))
                value = self.rrd.save(path, value, type, command, cmd.cycleTime)
                log.debug("rrd save result: %s" % value)
                for t in thresholds:
                    t.check(cmd.device, cmd.component, cmd.eventKey, value,
                            self.sendThresholdEvent)


    def fetchConfig(self):
        def doFetchConfig(driver):
            try:
                yield self.model.callRemote('propertyItems')
                self.setPropertyItems(driver.next())
                
                yield self.model.callRemote('getDefaultRRDCreateCommand')
                createCommand = driver.next()
                
                yield self.model.callRemote('getDataSourceCommands',
                                            self.options.device)
                self.updateConfig(driver.next())

                self.rrd = RRDUtil(createCommand, 60)

            except Exception, ex:
                log.exception(ex)
                raise

        return drive(doFetchConfig)
            

    def start(self, driver):
        try:
            yield self.fetchConfig()
            driver.next()
        except Exception, ex:
            log.exception(ex)
            raise
        driveLater(self.configCycleInterval * 60, self.start)


    def buildOptions(self):
        RRDDaemon.buildOptions(self)

        self.parser.add_option('--parallel', dest='parallel', 
                               default=50, type='int',
                               help="number of devices to collect at one time")
        
    def main(self):
        self.sendEvent(self.startevt)
        d = drive(self.start)
        d.addCallbacks(self.processSchedule, self.errorStop)
        if self.options.cycle:
            d.addCallback(self.heartbeatCycle)
        reactor.run()
        self.sendEvent(self.stopevt, now=True)


if __name__ == '__main__':
    z = zencommand()
    z.main()
