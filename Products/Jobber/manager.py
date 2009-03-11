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

from Globals import InitializeClass
import transaction
from zope.interface import implements

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM

from interfaces import *
from status import JobStatus, FAILURE
import time
from copy import copy
from Products.ZenUtils import guid

def manage_addJobManager(context, id="JobManager"):
    jm = JobManager(id)
    context._setObject(id, jm)
    return getattr(context, id)

class JobManager(ZenModelRM):

    implements(IJobManager)

    meta_type = portal_type = 'JobManager'

    _relations = (
        ("jobs",
         ToManyCont(
             ToOne, "Products.Jobber.status.JobStatus", "jobmanager"
         )
        ),
    )

    def _getId(self, klass=None):
        """
        Get a unique id for jobs.

        If C{klass} is not None, its __name__ attribute will be used as the id
        prefix.

        @return: A unique id.
        @rtype: str
        """
        if klass is not None:
            name = klass.__name__
        else:
            name = 'job'
        return "%s_%s" % (name, guid.generate())

    def addJob(self, klass, *args, **kwargs):
        """
        Create a new L{Job} and L{JobStatus} from the class specified.

        C{klass} must implement L{IJob} and should subclass L{Job}.

        @return: The L{JobStatus} object representing the job created.
        @rtype: L{JobStatus}
        """
        assert IJob.implementedBy(klass), ("JobManager.addJob can accept"
                                           " only IJob classes")
        jobid = self._getId(klass)
        instance = klass(jobid, *args, **kwargs)
        # Create the JobStatus representing this Job
        status = JobStatus(instance)
        self.jobs._setObject(status.id, status)
        transaction.commit()
        return self.jobs._getOb(status.id)

    def getJob(self, jobid):
        """
        Return a L{JobStatus} object that matches the id specified.

        @param jobid: id of the L{JobStatus}. The "JobStatus_" prefix is not
        necessary.
        @type jobid: str
        @return: A matching L{JobStatus} object, or None if none is found
        @rtype: L{JobStatus}, None
        """
        # Status objects have ids like 
        # "ShellCommandJobStatus_7680ef-9234-2875f0abc",
        # but we only care about the part at the end.
        uid = jobid.split('_')[-1]
        for jid in self.jobs.objectIds():
            if jid.endswith(uid):
                return self.jobs._getOb(jid)
        return None

    def getUnfinishedJobs(self):
        """
        Return JobStatus objects that have not yet completed, including those
        that have not yet started.

        @return: A list of jobs.
        @rtype: list
        """
        def isUnfinished(job):
            return not job.isFinished()
        return filter(isUnfinished, self.jobs())

    def getRunningJobs(self):
        """
        Return JobStatus objects that have started but not finished.

        @return: A list of jobs.
        @rtype: list
        """
        def isRunning(job):
            return not job.isFinished() and job.isStarted()
        return filter(isRunning, self.jobs())

    def getPendingJobs(self):
        """
        Return JobStatus objects that have not yet started.

        @return: A list of jobs.
        @rtype: list
        """
        def isPending(job):
            return not job.isStarted()
        return filter(isPending, self.jobs())

    def getFinishedJobs(self):
        """
        Return JobStatus objects that have finished.

        @return: A list of jobs.
        @rtype: list
        """
        def isFinished(job):
            return job.isFinished()
        return filter(isFinished, self.jobs())

    def deleteUntil(self, untiltime):
        """
        Delete all jobs older than untiltime.
        """
        for job in self.getFinishedJobs():
            if job.getTimes()[1] <= untiltime:
                job.delete()

    def clearJobs(self):
        """
        Clear out all finished jobs.
        """
        self.deleteUntil(time.time())

    def killRunning(self):
        """
        Cancel running jobs with FAILURE.
        """
        for job in self.getRunningJobs():
            job.interrupt()


InitializeClass(JobManager)
