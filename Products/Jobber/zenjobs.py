###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sys
import time
import logging
from Globals import *
from twisted.internet import reactor, defer
from Products.ZenUtils.CyclingDaemon import CyclingDaemon
import transaction
from status import FAILURE

logger = logging.getLogger('zen.Jobs')
logger.setLevel(20)

class ZenJobs(CyclingDaemon):
    """
    Daemon to run jobs.
    """
    name = 'zenjobs'

    def __init__(self, *args, **kwargs):
        CyclingDaemon.__init__(self, *args, **kwargs)
        self.jm = self.dmd.JobManager
        self.runningjobs = []

    def run_job(self, job):
        self.syncdb()
        logger.info("Starting %s %s" % (
            job.getJobType(),
            job.getDescription()))
        self.runningjobs.append(job.start())
        # Zope will want to know the job has started
        transaction.commit()
        job.getStatus().waitUntilFinished().addCallback(self.job_done)

    def job_done(self, jobstatus):
        logger.info('%s %s completed in %s seconds.' % (
            jobstatus.getJob().getJobType(),
            jobstatus.getJob().getDescription(),
            jobstatus.getDuration()))
        # Zope will want to know the job has finished
        transaction.commit()

    def waitUntilRunningJobsFinish(self):
        return defer.DeferredList(self.runningjobs)

    def main_loop(self):
        for job in self.get_new_jobs():
            self.run_job(job)
        self.finish_loop()

    def finish_loop(self):
        if self.options.cycle:
            self.sendHeartbeat()
            reactor.callLater(self.options.cycletime, self.runCycle)
        else:
            # Can't stop the reactor until jobs are done
            whenDone = self.waitUntilRunningJobsFinish()
            whenDone.addBoth(self.finish)

    def runCycle(self):
        try:
            start = time.time()
            self.syncdb()
            self.main_loop()
        except:
            self.log.exception("unexpected exception")
            reactor.callLater(self.options.cycletime, self.runCycle)

    def get_new_jobs(self):
        return [s.getJob() for s in self.jm.getPendingJobs()]

    def finish(self, r=None):
        for d in self.runningjobs:
            try:
                d.callback(FAILURE)
            except defer.AlreadyCalledError:
                pass
        CyclingDaemon.finish(self, r)

if __name__ == "__main__":
    zj = ZenJobs()
    zj.run()

