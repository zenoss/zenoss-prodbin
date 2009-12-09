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

__doc__ = """zenstatus

Check the TCP/IP connectivity of IP services.
UDP is specifically not supported.
"""

import time
from sets import Set

from twisted.internet import reactor, defer

import Globals # make zope imports work
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenStatus.ZenTcpClient import ZenTcpClient
from Products.ZenEvents.ZenEventClasses import Heartbeat

# required for pb.setUnjellyableForClass
from Products.ZenHub.services import StatusConfig
if 0:
    StatusConfig = None                 # pyflakes

class Status:
    """
    Class to track the status of all connection attempts to
    remote devices.
    """
    _running = 0
    _fail = 0
    _success = 0
    _start = 0
    _stop = 0
    _defer = None

    def __init__(self):
        self._remaining = []

    def start(self, jobs):
        """
        Start a scan cycle with the jobs to run.

        @parameter jobs: jobs to run
        @type jobs: list of job entries
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        self._success = 0
        self._stop = 0
        self._fail = 0
        self._running = 0
        self._remaining = jobs
        self._start = time.time()
        self._defer = defer.Deferred()
        if not self._remaining:
            self._stop = time.time()
            self._defer.callback(self)
        return self._defer

    def next(self):
        """
        Start and return the next job that can be scheduled to run.

        @return: job
        @rtype: Twisted deferred
        """
        job = self._remaining.pop()
        d = job.start()
        d.addCallbacks(self.success, self.failure)
        self._running += 1
        return d

    def testStop(self, result):
        """
        Cleanup completed jobs and update stats.

        @parameter result: ignored
        @type result: Twisted deferred
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        self._running -= 1
        if self.done():
            self._stop = time.time()
            self._defer, d = None, self._defer
            d.callback(self)
        return result

    def success(self, result):
        """
        Record a successful job.

        @parameter result: ignored
        @type result: Twisted deferred
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        self._success += 1
        return self.testStop(result)

    def failure(self, result):
        """
        Record a failed job.

        @parameter result: ignored
        @type result: Twisted deferred
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        self._failure += 1
        return self.testStop(result)

    def done(self):
        """
        Are we done yet?

        @return: is there anything left to do?
        @rtype: boolean
        """
        return self._running == 0 and not self._remaining

    def stats(self):
        """
        Report on the number of remaining, running,
        successful and failed jobs.

        @return: counts of job status
        @rtype: tuple of ints
        """
        return (len(self._remaining),
                self._running,
                self._success,
                self._fail)

    def duration(self):
        """
        Total time that the daemon has been running jobs
        this scan cycle.
        """
        if self.done():
            return self._stop - self._start
        return time.time() - self._start


class ZenStatus(PBDaemon):
    """
    Daemon class to attach to zenhub and pass along
    device configuration information.
    """
    name = agent = "zenstatus"
    initialServices = ['EventService', 'StatusConfig']
    statusCycleInterval = 300
    configCycleInterval = 20
    properties = ('statusCycleInterval', 'configCycleInterval')
    reconfigureTimeout = None

    def __init__(self):
        PBDaemon.__init__(self, keeproot=True)
        self.clients = {}
        self.counts = {}
        self.status = Status()

    def configService(self):
        """
        Return a connection to a status service.

        @return: service to gather configuration
        @rtype: Twisted deferred
        """
        return self.services.get('StatusConfig', FakeRemote())

    def startScan(self, ignored=None):
        """
        Start gathering status information, taking care of the case where
        we are invoked as a daemon or for a single run.
        """
        d = drive(self.scanCycle)
        if not self.options.cycle:
            d.addBoth(lambda unused: self.stop())

    def connected(self):
        """
        Gather our configuration and start collecting status information.
        Called after connected to the zenhub service.
        """
        d = drive(self.configCycle)
        d.addCallbacks(self.startScan, self.configError)

    def configError(self, why):
        """
        Log errors that have occurred gathering our configuration

        @param why: error message
        @type why: Twisted error instance
        """
        self.log.error(why.getErrorMessage())
        self.stop()

    def remote_notifyConfigChanged(self):
        """
        Procedure called from zenhub to get us to re-gather all
        of our configuration.
        """
        self.log.debug("Notification of config change from zenhub")
        if self.reconfigureTimeout and not self.reconfigureTimeout.called:
            self.reconfigureTimeout.cancel()
        self.reconfigureTimeout = reactor.callLater(
            self.statusCycleInterval/2, drive, self.reconfigure)

    def remote_setPropertyItems(self, items):
        """
        Procedure called from zenhub to pass in new properties.

        @parameter items: items to update
        @type items: list
        """
        self.log.debug("Update of collection properties from zenhub")
        self.setPropertyItems(items)

    def setPropertyItems(self, items):
        """
        Extract configuration elements used by this server.

        @parameter items: items to update
        @type items: list
        """
        table = dict(items)
        for name in self.properties:
            value = table.get(name, None)
            if value is not None:
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)

    def remote_deleteDevice(self, device):
        """
        Remove any devices that zenhub tells us no longer exist.

        @parameter device: name of device to delete
        @type device: string
        """
        self.ipservices = [s for s in self.ipservices if s.cfg.device != device]

    def configCycle(self, driver):
        """
        Get our configuration from zenhub

        @parameter driver: object
        @type driver: Twisted deferred object
        """
        now = time.time()
        self.log.info("Fetching property items")
        yield self.configService().callRemote('propertyItems')
        self.setPropertyItems(driver.next())

        self.log.info("Fetching default RRDCreateCommand")
        yield self.configService().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.log.info("Getting threshold classes")
        yield self.configService().callRemote('getThresholdClasses')
        self.remote_updateThresholdClasses(driver.next())

        self.log.info("Getting collector thresholds")
        yield self.configService().callRemote('getCollectorThresholds')
        self.rrdStats.config(self.options.monitor, self.name, driver.next(),
                             createCommand)

        d = driveLater(self.configCycleInterval * 60, self.configCycle)
        d.addErrback(self.error)

        yield drive(self.reconfigure)
        driver.next()

        self.rrdStats.gauge('configTime',
                            self.configCycleInterval * 60,
                            time.time() - now)

    def reconfigure(self, driver):
        """
        Contact zenhub and gather our configuration again.

        @parameter driver: object
        @type driver: Twisted deferred object
        """
        self.log.debug("Getting service status")
        yield self.configService().callRemote('serviceStatus')
        self.counts = {}
        for (device, component), count in driver.next():
            self.counts[device, component] = count

        self.log.debug("Getting services for %s", self.options.configpath)
        yield self.configService().callRemote('services',
                                              self.options.configpath)
        self.ipservices = []
        for s in driver.next():
            if self.options.device and s.device != self.options.device:
                continue
            count = self.counts.get((s.device, s.component), 0)
            self.ipservices.append(ZenTcpClient(s, count))
        self.log.debug("ZenStatus configured with %d checks",
                       len(self.ipservices))


    def error(self, why):
        """
        Log errors that have occurred

        @param why: error message
        @type why: Twisted error instance
        """
        self.log.error(why.getErrorMessage())

    def scanCycle(self, driver):
        """
        Go through all devices and start determining the status of each
        TCP service.

        @parameter driver: object
        @type driver: Twisted deferred object
        """
        d = driveLater(self.statusCycleInterval, self.scanCycle)
        d.addErrback(self.error)

        if not self.status.done():
            duration = self.status.duration()
            self.log.warning("Scan cycle not complete in %.2f seconds",
                             duration)
            if duration < self.statusCycleInterval * 2:
                self.log.warning("Waiting for the cycle to complete")
                return
            self.log.warning("Restarting jobs for another cycle")

        self.log.debug("Getting down devices")
        yield self.eventService().callRemote('getDevicePingIssues')
        ignored = Set([s[0] for s in driver.next()])

        self.log.debug("Starting scan")
        d = self.status.start([i for i in self.ipservices
                               if i.cfg.device not in ignored])
        self.log.debug("Running jobs")
        self.runSomeJobs()
        yield d
        driver.next()
        self.log.debug("Scan complete")
        self.heartbeat()

    def heartbeat(self):
        """
        Twisted keep-alive mechanism to ensure that
        we're still connected to zenhub.
        """
        _, _, success, fail = self.status.stats()
        self.log.info("Finished %d jobs (%d good, %d bad) in %.2f seconds",
                      (success + fail), success, fail, self.status.duration())
        if not self.options.cycle:
            self.stop()
            return
        heartbeatevt = dict(eventClass=Heartbeat,
                            component=self.name,
                            device=self.options.monitor)
        self.sendEvent(heartbeatevt, timeout=self.statusCycleInterval*3)
        self.niceDoggie(self.statusCycleInterval)
        for ev in (self.rrdStats.gauge('cycleTime',
                                       self.statusCycleInterval,
                                       self.status.duration()) +
                   self.rrdStats.gauge('success',
                                       self.statusCycleInterval,
                                       success) +
                   self.rrdStats.gauge('failed',
                                       self.statusCycleInterval,
                                       fail)):
            self.sendEvent(ev)


    def runSomeJobs(self):
        """
        Run IP service tests with the maximum parallelization
        allowed.
        """
        while 1:
            left, running, good, bad = self.status.stats()
            if not left or running >= self.options.parallel:
                break
            self.log.debug("Status: left %d running %d good %d bad %d",
                           left, running, good, bad)
            d = self.status.next()
            d.addCallbacks(self.processTest, self.processError)
            self.log.debug("Started job")

    def processTest(self, job):
        """
        Test a connection to a device.

        @parameter job: device and TCP service to test
        @type job: ZenTcpClient object
        """
        self.runSomeJobs()
        key = job.cfg.device, job.cfg.component
        evt = job.getEvent()
        if evt:
            self.sendEvent(evt)
            self.counts.setdefault(key, 0)
            self.counts[key] += 1
        else:
            if key in self.counts:
                # TODO: Explain why we care about resetting the count
                del self.counts[key]

    def processError(self, error):
        """
        Log errors that have occurred from testing TCP services

        @param error: error message
        @type error: Twisted error instance
        """
        self.log.warn(error.getErrorMessage())

    def buildOptions(self):
        """
        Build our list of command-line options
        """
        PBDaemon.buildOptions(self)
        self.parser.add_option('--configpath',
                     dest='configpath',
                     default="/Devices/Server",
                     help="Path to our monitor config ie: /Devices/Server")
        self.parser.add_option('--parallel',
                     dest='parallel',
                     type='int',
                     default=50,
                     help="Number of devices to collect at one time")
        self.parser.add_option('--cycletime',
                     dest='cycletime',
                     type="int",
                     default=60,
                     help="Check events every cycletime seconds")
        self.parser.add_option('-d', '--device', dest='device',
                help="Device's DMD name ie www.example.com")

if __name__=='__main__':
    pm = ZenStatus()
    pm.run()
