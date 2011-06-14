###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from Globals import *
from ZODB.transact import transact
from Products.ZenEvents.UpdateCheck import UpdateCheck
from Products.ZenEvents.Schedule import Schedule
from twisted.internet import reactor, defer
from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop
from Products.ZenUtils.CyclingDaemon import CyclingDaemon
import transaction
from status import FAILURE

logger = logging.getLogger('zen.Jobs')

class ZenJobs(CyclingDaemon):
    """
    Daemon to run jobs.
    """
    name = 'zenjobs'

    def __init__(self, *args, **kwargs):
        CyclingDaemon.__init__(self, *args, **kwargs)
        self.jm = self.dmd.JobManager
        self.runningjobs = []

        self.schedule = Schedule(self.options, self.dmd)
        self.schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
        self.schedule.monitor = self.options.monitor

        self.updateCheck = UpdateCheck()

        # Send startup event
        if self.options.cycle:
            event = Event(device=self.options.monitor,
                      eventClass=App_Start,
                      summary="zenjobs started",
                      severity=0, component="zenjobs")
            self.sendEvent(event)

    @defer.inlineCallbacks
    def run_job(self, job):
        self.syncdb()
        logger.info("Starting %s %s" % (
            job.getJobType(),
            job.getDescription()))
        d = job.getStatus().waitUntilFinished()
        d.addCallback(self.job_done)
        jobd = job.start()
        # Zope will want to know the job has started
        transaction.commit()
        self.runningjobs.append(jobd)
        yield jobd

    def job_done(self, jobstatus):
        logger.info('%s %s completed in %s seconds.' % (
            jobstatus.getJob().getJobType(),
            jobstatus.getJob().getDescription(),
            jobstatus.getDuration()))
        # Zope will want to know the job has finished
        transaction.commit()

    def waitUntilRunningJobsFinish(self):
        return defer.DeferredList(self.runningjobs)

    @transact
    def checkVersion(self, zem):
        self.syncdb()
        self.updateCheck.check(self.dmd, zem)

    @defer.inlineCallbacks
    def main_loop(self):
        zem = self.dmd.ZenEventManager
        self.checkVersion(zem)
        for job in self.get_new_jobs():
            yield self.run_job(job)
        yield self.finish_loop()

    def finish_loop(self):
        if not self.options.cycle:
            # Can't stop the reactor until jobs are done
            whenDone = self.waitUntilRunningJobsFinish()
            whenDone.addBoth(self.finish)

    def get_new_jobs(self):
        return [s.getJob() for s in self.jm.getPendingJobs()]

    def finish(self, r=None):
        for d in self.runningjobs:
            try:
                d.callback(FAILURE)
            except defer.AlreadyCalledError:
                pass
        CyclingDaemon.finish(self, r)

    def run(self):
        def startup():
            self.schedule.start()
            self.runCycle()
        reactor.callWhenRunning(startup)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)
        reactor.run()

    def stop(self):
        self.running = False
        self.log.info("stopping")
        if self.options.cycle:
            self.sendEvent(Event(device=self.options.monitor,
                             eventClass=App_Stop,
                             summary="zenjobs stopped",
                             severity=3, component="zenjobs"))

if __name__ == "__main__":
    zj = ZenJobs()
    zj.run()

