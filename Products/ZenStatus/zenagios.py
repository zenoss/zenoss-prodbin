#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import time
import logging
log = logging.getLogger("zen.zenagios")

from twisted.internet import reactor, defer
from twisted.internet.protocol import ProcessProtocol
from twisted.python import failure

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenEvents import Event

from Products.ZenRRD.RRDDaemon import RRDDaemon

from sets import Set

MAX=2

class TimeoutError(Exception): pass

def Timeout(deferred, seconds):
    def _timeout(deferred):
        deferred.errback(failure.Failure(TimeoutError))
    def _cb(arg, timer):
        if not timer.called:
            timer.cancel()
        return arg
    timer = reactor.callLater(seconds, _timeout, deferred)
    deferred.addBoth(_cb, timer)
    return deferred

class Cmd(ProcessProtocol):
    device = None
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
    stopped = None
    result = None

    def __init__(self):
        self.output = []
        self.error = []

    def name(self):
        cmd, args = self.command.split(' ', 1)
        cmd = cmd.split('/')[-1]
        if len(args) > 10:
            return '%s %s...%s' % (cmd, args[:10], args[-10:])
        return '%s %s' % (cmd, args)

    def nextRun(self):
        if self.running():
            return self.lastStart
        return self.lastStop + self.cycleTime

    def start(self):
        log.debug('Process %s started' % self.name())
        self.lastStart = time.time()
        reactor.spawnProcess(self, '/bin/sh',
                             ('/bin/sh', '-c', 'exec ' + self.command))
        self.stopped = Timeout(defer.Deferred(), MAX)
        self.stopped.addErrback(self.timeout)
        return self.stopped

    def timeout(self, ignored):
        self.transport.signalProcess('KILL')
        return ignored

    def running(self):
        return self.lastStop < self.lastStart 

    def outReceived(self, data):
        log.debug('%s got data: %s' % (self.name(), `data`))
        self.output.append(data)

    def errReceived(self, err):
        log.debug('got error: %s' % `err`)
        self.error.append(err)

    def processEnded(self, reason):
        log.debug('Process %s stopped (%s), %f elapsed' % (
            self.name(),
            reason.value.exitCode,
            self.lastStop - self.lastStart))

        self.lastStop = time.time()
        self.result = reason
        self.output = [s.strip() for s in ''.join(self.output).split('\n')][0]
        self.error = ''.join(self.error)
        if self.stopped:
            d, self.stopped = self.stopped, None
            d.callback(self)
        self.stopped = None

    def updateConfig(self,device,username, password, useSsh,
                     cycleTime, eventKey, eventClass, component, severity,
                     command, **kw):
        self.device = device
        self.username = username
        self.password = password
        self.useSsh = useSsh
        self.cycleTime = max(cycleTime, 1)
        self.eventKey = eventKey
        self.eventClass = eventClass
        self.component = component
        self.severity = severity
        self.command = command
        
class zenagios(RRDDaemon):
    heartbeatTimeout = RRDDaemon.configCycleInterval*3
    properties = RRDDaemon.properties + ("configCycleInterval",)

    def __init__(self):
        RRDDaemon.__init__(self, 'zenagios')
        self.schedule = []
        self.timeout = None
        self.deviceIssues = Set()
        self.flushEvents()

    def flushEvents(self):
        self.sendEvents()
        reactor.callLater(1, self.flushEvents)

    def updateConfig(self, config):
        table = dict([((c.device,c.command), c) for c in self.schedule])

        for c in config:
            device, username, password, commandPart = c
            for cmd in commandPart:
                (useSsh, cycleTime,
                 eventKey, eventClass, component, severity, command) = cmd
                obj = table.setdefault((device,command), Cmd())
                args = locals().copy()
                del args['self']
                obj.updateConfig(**args)
        self.schedule = table.values()
        if self.options.cycle:
            self.heartbeat()

    def setPropertyItems(self, items):
        RRDDaemon.setPropertyItems(self, items)
        heartbeatTimeout = self.configCycleInterval*3

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
            if self.timeout:
                self.timeout.cancel()
            self.schedule.sort(key=Cmd.nextRun)
            earliest = None
            running = 0
            for c in self.schedule:
                if c.running():
                    running += 1
                elif c.nextRun() <= time.time():
                    c.start().addBoth(self.finished)
                    running += 1
                else:
                    earliest = c.nextRun()
                    break
                if running >= self.options.parallel:
                    break
            if earliest is not None:
                self.timeout = reactor.callLater(earliest, self.processSchedule)
        except Exception, ex:
            log.exception(ex)
            
    def finished(self, cmd):
        if isinstance(cmd, failure.Failure):
            log.exception(cmd.value)
            return
        msg, values = cmd.output.split('|', 1)
        exitCode = cmd.result.value.exitCode
        severity = cmd.severity
        issueKey = cmd.device, cmd.eventClass
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
        self.processSchedule()

    def fetchConfig(self):
        def doFetchConfig(driver):
            try:
                yield self.model.callRemote('propertyItems')
                self.setPropertyItems(driver.next())
                
                yield self.model.callRemote('getNagiosCmds')
                self.updateConfig(driver.next())
            except Exception, ex:
                log.exception(ex)
                raise
        return drive(doFetchConfig)
            

    def start(self, driver):
        try:
            yield self.fetchConfig()
            n = driver.next()
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
        drive(self.start).addCallbacks(self.processSchedule, self.error)
        reactor.run(installSignalHandlers=False)
        self.sendEvent(self.stopevt, now=True)


if __name__ == '__main__':
    z = zenagios()
    z.main()
