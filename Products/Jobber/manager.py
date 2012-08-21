##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
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
from Products.Five.browser import BrowserView
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.celeryintegration import Task
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from .jobs import Job
from .exceptions import NoSuchJobException

from logging import getLogger
log = getLogger("zen.JobManager")

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

    def addJob(self, klass, description=None, args=None, kwargs=None, properties=None):
        """
        Schedule a new L{Job} from the class specified.

        NOTE: The job WILL NOT run until you commit the transaction!

        @return: An JobRecord object that can be used to check on the job
        results or abort the job
        @rtype: L{JobRecord}
        """
        log.debug("Adding job %s", klass)
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Push the task out to AMQP
        async_result = klass().delay(*args, **kwargs)

        # Put a pending job in the database. zenjobs will wait to run this job
        # until it exists.
        try:
            description = description or klass.getJobDescription(*args, **kwargs)
        except Exception:
            description = "%s %r properties=%r" % (args, kwargs, properties)

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
        for prop,propval in properties.iteritems():
            setattr(meta, prop, propval)

        self._setOb(async_result.task_id, meta)
        job = self._getOb(async_result.task_id)
        self.getCatalog().catalog_object(job)
        log.debug("Created job %s: %s", klass, async_result.task_id)
        return job

    def wait(self, job_id):
        return self.getJob(job_id).wait()

    def update(self, job_id, **kwargs):
        log.debug("Updating job %s", job_id)
        job = self.getJob(job_id)
        job.update(kwargs)
        self.getCatalog().catalog_object(job)

    def getJob(self, jobid):
        """
        Return a L{JobStatus} object that matches the id specified.

        @param jobid: id of the L{JobStatus}. The "JobStatus_" prefix is not
        necessary.
        @type jobid: str
        @return: A matching L{JobStatus} object, or raises a NoSuchJobException if none is found
        @rtype: L{JobStatus}, None
        """
        if not jobid:
            raise NoSuchJobException(jobid)
        try:
            return self._getOb(jobid)
        except AttributeError:
            raise NoSuchJobException(jobid)

    def deleteJob(self, jobid):
        job = self.getJob(jobid)
        if not job.isFinished():
            job.abort()
        # Clean up the log file
        if getattr(job, 'logfile', None) is not None:
            try:
                os.remove(job.logfile)
            except (OSError, IOError):
                # Did our best!
                pass
        self.getCatalog().uncatalog_object('/'.join(job.getPhysicalPath()))
        return self._delObject(jobid)

    def _getByStatus(self, statuses, jobtype=None):
        def _normalizeJobType(typ):
            if typ is not None and isinstance(typ, type):
                if hasattr(typ, 'getJobType'):
                    return typ.getJobType()
                else:
                    return typ.__name__
            return typ

        # build additional query qualifiers based on named args
        query = {}
        if jobtype is not None:
            query['type'] = _normalizeJobType(jobtype)

        for b in self.getCatalog()(status=list(statuses), **query):
            yield b.getObject()

    def getUnfinishedJobs(self, type_=None):
        """
        Return JobRecord objects that have not yet completed, including those
        that have not yet started.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.UNREADY_STATES, type_)

    def getRunningJobs(self, type_=None):
        """
        Return JobRecord objects that have started but not finished.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus((states.STARTED, states.RETRY), type_)

    def getPendingJobs(self, type_=None):
        """
        Return JobRecord objects that have not yet started.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus((states.RECEIVED, states.PENDING), type_)

    def getFinishedJobs(self, type_=None):
        """
        Return JobRecord objects that have finished.

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.READY_STATES, type_)

    def getAllJobs(self, type_=None):
        """
        Return all .

        @return: All jobs in the requested state.
        @rtype: generator
        """
        return self._getByStatus(states.ALL_STATES, type_)
        
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


class JobLogDownload(BrowserView):

    def __call__(self):
        response = self.request.response
        try:
            jobid = self.request.get('job')
            jobrecord = self.context.JobManager.getJob(jobid)
            logfile = jobrecord.logfile
        except (KeyError, AttributeError, NoSuchJobException):
            response.setStatus(404)
        else:
            response.setHeader('Content-Type', 'text/plain')
            response.setHeader('Content-Disposition', 'attachment;filename=%s' % os.path.basename(logfile))
            with open(logfile, 'r') as f:
                return f.read()
