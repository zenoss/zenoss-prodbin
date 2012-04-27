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
import time
from copy import copy
from datetime import datetime

import transaction
from Acquisition import aq_base
from AccessControl import getSecurityManager
from celery import states
from OFS.ObjectManager import ObjectManager
from persistent.dict import PersistentDict
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.celeryintegration import Task
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from .exceptions import NoSuchJobException


CATALOG_NAME = "job_catalog"


def manage_addJobManager(context, id="JobManager"):
    jm = JobManager(id)
    context._setObject(id, jm)
    return getattr(context, id)


class JobRecord(ObjectManager):

    def __init__(self, *args, **kwargs):
        ObjectManager.__init__(self, *args)
        self.job_description = None
        self.user = None
        self.job_type = None
        self.job_description = None
        self.status = states.PENDING
        self.date_schedule = None
        self.date_started = None
        self.date_done = None
        self.result = None
        self.update(kwargs)

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    @property
    def _async_result(self):
        return Task.AsyncResult(self.getId())

    def abort(self):
        # This will occur immediately.
        return self._async_result.abort()

    def wait(self):
        return self._async_result.wait()

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)

    def isFinished(self):
        return getattr(self, 'status', None) in states.READY_STATES

    def getId(self):
        return getattr(aq_base(self), 'id', None)

    @property
    def uuid(self):
        return self.getId()

    @property
    def description(self):
        return self.job_description

    @property
    def type(self):
        return self.job_type

    @property
    def scheduled(self):
        return self.date_scheduled

    @property
    def started(self):
        return self.date_started

    @property
    def finished(self):
        return self.date_done



class JobManager(ZenModelRM):

    meta_type = portal_type = 'JobManager'

    def getCatalog(self):
        try:
            return self._getOb(CATALOG_NAME)
        except AttributeError:
            from Products.ZCatalog.ZCatalog import manage_addZCatalog

            # Make catalog for Devices
            manage_addZCatalog(self, CATALOG_NAME, CATALOG_NAME)
            zcat = self._getOb(CATALOG_NAME)
            cat = zcat._catalog
            for idxname in ['status', 'type', 'user']:
                cat.addIndex(idxname, makeCaseInsensitiveFieldIndex(idxname))
            for idxname in ['scheduled', 'started', 'finished']:
                cat.addIndex(idxname, DateIndex(idxname))
            return zcat

    def addJob(self, klass, description=None, args=None, kwargs=None):
        """
        Schedule a new L{Job} from the class specified.

        NOTE: The job WILL NOT run until you commit the transaction!

        @return: An JobRecord object that can be used to check on the job
        results or abort the job
        @rtype: L{JobRecord}
        """
        args = args or ()
        kwargs = kwargs or {}

        # Push the task out to AMQP
        async_result = klass().delay(*args, **kwargs)

        # Put a pending job in the database. zenjobs will wait to run this job
        # until it exists.
        try:
            description = description or klass.getJobDescription(*args, **kwargs)
        except Exception:
            description = "%s %s" % (args, kwargs)

        user = getSecurityManager().getUser()
        if not isinstance(user, basestring):
            user = user.getId()
        meta = JobRecord(id=async_result.task_id,
                         user=user,
                         job_type=klass.getJobType(),
                         job_description=description,
                         status=states.PENDING,
                         date_scheduled=datetime.utcnow(),
                         date_started=None,
                         date_done=None,
                         result=None)
        self._setOb(async_result.task_id, meta)
        job = self._getOb(async_result.task_id)
        self.getCatalog().catalog_object(job)
        return job

    def wait(self, job_id):
        return self.getJob(job_id).wait()

    def update(self, job_id, **kwargs):
        job = self.getJob(job_id)
        job.update(kwargs)
        self.getCatalog().catalog_object(job)

    def getJob(self, jobid):
        """
        Return a L{JobStatus} object that matches the id specified.

        @param jobid: id of the L{JobStatus}. The "JobStatus_" prefix is not
        necessary.
        @type jobid: str
        @return: A matching L{JobStatus} object, or None if none is found
        @rtype: L{JobStatus}, None
        """
        try:
            return self._getOb(jobid)
        except AttributeError:
            raise NoSuchJobException(jobid)

    def deleteJob(self, jobid):
        job = self.getJob(jobid)
        if not job.isFinished():
            job.abort()
        self.getCatalog().uncatalog_object('/'.join(job.getPhysicalPath()))
        return self._delObject(jobid)

    def _getByStatus(self, *status):
        for b in self.getCatalog()(status=status):
            yield b.getObject()

    def getUnfinishedJobs(self):
        """
        Return JobRecord objects that have not yet completed, including those
        that have not yet started.

        @return: A list of jobs.
        @rtype: list
        """
        return self._getByStatus(*states.UNREADY_STATES)

    def getRunningJobs(self):
        """
        Return JobStatus objects that have started but not finished.

        @return: A list of jobs.
        @rtype: list
        """
        return self._getByStatus(states.STARTED, states.RETRY)

    def getPendingJobs(self):
        """
        Return JobStatus objects that have not yet started.

        @return: A list of jobs.
        @rtype: list
        """
        return self._getByStatus(states.RECEIVED, states.PENDING)

    def getFinishedJobs(self):
        """
        Return JobStatus objects that have finished.

        @return: A list of jobs.
        @rtype: list
        """
        return self._getByStatus(*states.READY_STATES)

    def deleteUntil(self, untiltime):
        """
        Delete all jobs older than untiltime.
        """

    def clearJobs(self):
        """
        Clear out all finished jobs.
        """
        for b in self.getCatalog()():
            self.deleteJob(b.getObject().getId())

    def killRunning(self):
        """
        Abort running jobs.
        """
        for job in self.getUnfinishedJobs():
            job.abort()
