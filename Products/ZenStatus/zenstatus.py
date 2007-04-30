###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import time
import sys

from twisted.internet import reactor, defer

import Globals # make zope imports work
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon as Base
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenStatus.ZenTcpClient import ZenTcpClient
from Products.ZenEvents.ZenEventClasses import Heartbeat

class Status:
    _running = 0
    _fail = 0
    _success = 0
    _start = 0
    _stop = 0
    _defer = None

    def __init__(self):
        self._remaining = []

    def start(self, jobs):
        self._remaining = jobs
        self._start = time.time()
        self._defer = defer.Deferred()
        if not self._remaining:
            self._stop = time.time()
            self._defer.callback(self)
        return self._defer

    def next(self):
        d = self._remaining.pop().start()
        d.addCallbacks(self.success, self.failure)
        self._running += 1
        return d

    def testStop(self, result):
        self._running -= 1
        if self.done():
            self._stop = time.time()
            self._defer, d = None, self._defer
            d.callback(self)
        return result

    def success(self, result):
        self._success += 1 
        return self.testStop(result)

    def failure(self, result):
        self._failure += 1
        return self.testStop(result)

    def done(self):
        return self._running == 0 and not self._remaining

    def stats(self):
        return (len(self._remaining),
                self._running,
                self._success,
                self._fail)

    def duration(self):
        if self.done():
            return self._stop - self._start
        return time.time() - self._start


class ZenStatus(Base):

    agent = "zenstatus"
    initialServices = ['EventService', 'StatusConfig']
    statusCycleInterval = 300
    configCycleInterval = 20
    properties = ('statusCycleInterval', 'configCycleInterval')
    reconfigureTimeout = None

    def __init__(self):
        Base.__init__(self, keeproot=True)
        self.clients = {}
        self.counts = {}
        self.status = Status()

    def configService(self):
        return self.services.get('StatusConfig', FakeRemote())

    def startScan(self, ignored=None):
        d = drive(self.scanCycle)
        if not self.options.cycle:
            d.addBoth(lambda x: self.stop())

    def connected(self):
        d = drive(self.configCycle)
        d.addCallbacks(self.startScan, self.configError)

    def configError(self, why):
        self.log.error(why.getErrorMessage())
        self.stop()

    def remote_notifyConfigChanged(self):
        if self.reconfigureTimeout and not self.reconfigureTimeout.called:
            self.reconfigureTimeout.cancel()
        self.reconfigureTimeout = reactor.callLater(5, drive, self.reconfigure)

    def remote_setPropertyItems(self, items):
        self.log.debug("Async update of collection properties")
        self.setPropertyItems(items)

    def setPropertyItems(self, items):
        'extract configuration elements used by this server'
        table = dict(items)
        for name in self.properties:
            value = table.get(name, None)
            if value is not None:
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)

    def remote_deleteDevice(self, device):
        self.ipservices = [s for s in self.ipservices if s.cfg.device != device]

    def configCycle(self, driver):
        self.log.info("fetching property items")
        yield self.configService().callRemote('propertyItems')
        self.setPropertyItems(driver.next())

        d = driveLater(self.configCycleInterval * 60, self.configCycle)
        d.addErrback(self.error)

        yield drive(self.reconfigure)
        driver.next()

    def reconfigure(self, driver):
        self.log.debug("Getting service status")
        yield self.configService().callRemote('serviceStatus')
        self.counts = {}
        for (device, component), count in driver.next():
            self.counts[device, component] = count

        self.log.debug("Getting services")
        yield self.configService().callRemote('services',
                                              self.options.configpath)
        self.ipservices = []
        for s in driver.next():
            count = self.counts.get((s.device, s.component), 0)
            self.ipservices.append(ZenTcpClient(s, count))
        self.log.debug("ZenStatus configured")
        

    def error(self, why):
        self.log.error(why.getErrorMessage())

    def scanCycle(self, driver):
        d = driveLater(self.statusCycleInterval, self.scanCycle)
        d.addErrback(self.error)

        if not self.status.done():
            duration = self.status.duration()
            self.log.warning("Scan cycle not complete in %.2f seconds",
                             duration)
            if duration < self.statusCycleInterval * 2:
                self.log.warning("Waiting for the cycle to complete")
                return
            self.log.warning("Ditching this cycle")

        self.log.debug("Getting down devices")
        yield self.eventService().callRemote('getDevicePingIssues')
        self.pingStatus = driver.next()

        self.log.debug("Starting scan")
        d = self.status.start(self.ipservices)
        self.log.debug("Running jobs")
        self.runSomeJobs()
        yield d 
        driver.next()
        self.log.debug("Scan complete")
        self.heartbeat()
        
    def heartbeat(self):
        _, _, success, fail = self.status.stats()
        self.log.info("Finished %d jobs (%d good, %d bad) in %.2f seconds",
                      (success + fail), success, fail, self.status.duration())
        if not self.options.cycle:
            self.stop
            return
        from socket import getfqdn
        heartbeatevt = dict(eventClass=Heartbeat,
                            component='ZenStatus',
                            device=getfqdn())
        self.sendEvent(heartbeatevt, timeout=self.statusCycleInterval*3)


    def runSomeJobs(self):
        while 1:
            left, running, good, bad = self.status.stats()
            self.log.debug("Status: left %d running %d good %d bad %d",
                           left, running, good, bad)
            if not left or running >= self.options.parallel:
                break
            d = self.status.next()
            d.addCallbacks(self.processTest, self.processError)
            self.log.debug("Started job")

    def processTest(self, job):
        self.runSomeJobs()
        key = job.cfg.device, job.cfg.component
        evt = job.getEvent()
        if evt:
            self.sendEvent(evt)
            self.counts.setdefault(key, 0)
            self.counts[key] += 1
        else:
            if key in self.counts:
                del self.counts[key] 
        
    def processError(self, error):
        self.log.warn(error.getErrorMessage())

    def buildOptions(self):
        Base.buildOptions(self)
        p = self.parser
        p.add_option('--configpath',
                     dest='configpath',
                     default="/Devices/Server",
                     help="path to our monitor config ie: /Devices/Server")
        p.add_option('--parallel',
                     dest='parallel', 
                     type='int',
                     default=50,
                     help="number of devices to collect at one time")
        p.add_option('--cycletime',
                     dest='cycletime',
                     type="int",
                     default=60,
                     help="check events every cycletime seconds")


if __name__=='__main__':
    pm = ZenStatus()
    pm.run()
