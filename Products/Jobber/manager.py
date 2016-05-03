##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os

from datetime import datetime, timedelta
from uuid import uuid4

import transaction

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from AccessControl import getSecurityManager
from OFS.ObjectManager import ObjectManager
from Products.PluginIndexes.DateIndex.DateIndex import DateIndex
from Products.Five.browser import BrowserView
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.celeryintegration import current_app, states, chain
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from ZODB.POSException import ConflictError
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD, ZEN_ADD

from .exceptions import NoSuchJobException
from .jobs import Job

from logging import getLogger
log = getLogger("zen.JobManager")

CATALOG_NAME = "job_catalog"


def _dispatchTask(task, **kwargs):
    """
    Delay the actual scheduling of the job until the transaction manages
    to get itself committed. This prevents Celery from getting a new task
    for every retry in the event of ConflictErrors. See ZEN-2704.
    """
    opts = dict(kwargs)
    # Have to use a closure because of Celery's funky signature inspection
    # and because of the status argument transaction passes
    def hook(ignored):
        log.info("Dispatching %s job to zenjobs: %s", type(task), task)
        # Push the task out to AMQP (ignore returned object).
        task.apply_async(**opts)
    transaction.get().addAfterCommitHook(hook)


def manage_addJobManager(context, id="JobManager"):
    jm = JobManager(id)
    context._setObject(id, jm)
    return getattr(context, id)


class JobRecord(ObjectManager):

    errors = ""
    
    def __init__(self, *args, **kwargs):
        ObjectManager.__init__(self, *args)
        self.user = None
        self.job_name = None
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
        if not self.job_name:
            tasks = current_app.tasks.values()
            for task in (t for t in tasks if isinstance(t, Job)):
                if task.getJobType() == self.job_type:
                    self.job_name = task.name
                    break
            else:
                raise AttributeError(
                        "No job class associated with job %s" % self.id
                    )
        return current_app.tasks[self.job_name].AsyncResult(self.getId())

    def abort(self):
        # This will occur immediately.
        return self._async_result.abort()

    def wait(self):
        return self._async_result.wait()

    def update(self, d):
        for k, v in d.iteritems():
            setattr(self, k, v)
        if self.isFinished():
            self.errors = self._parseErrors()

    def _parseErrors(self):
        if not hasattr(self, "logfile"):
            return ""
        try:
            with open(self.logfile, 'r') as f:
                buffer = f.readlines()
                # look for error level log lines
                return "\n".join([ line for line in buffer if "ERROR zen." in line])
        except (IOError, AttributeError, TypeError):
            return ""

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

    security = ClassSecurityInfo()
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

    security.declareProtected(ZEN_ADD, 'addJobChain')
    def addJobChain(self, *joblist, **options):
        """
        Submit a list of SubJob objects that will execute in list order.
        If options are specified, they are applied to each subjob; options
        that were specified directly on the subjob are not overridden.

        Supported options include:
            immutable {bool} Set True to 'freeze' the job arguments.
            ignoreresult {bool} Set True to drop the result of the jobs.

        If both options are not set, they default to False, which means the
        result of the prior job is passed to the next job as argument(s).

        NOTE: The jobs will not start until you commit the transaction.

        @returns A list of JobRecord objects.
        """
        subtasks = []
        records = []
        for subjob in joblist:
            task_id = str(uuid4())
            opts = dict(task_id=task_id, **options)
            opts.update(subjob.options)
            subtask = subjob.job.subtask(
                    args=subjob.args, kwargs=subjob.kwargs, **opts
                )
            records.append(self._savejobrecord(
                task_id, subjob.job, subjob.description,
                subjob.args, subjob.kwargs
            ))
            subtasks.append(subtask)
        task = chain(*subtasks)

        # Dispatch job to zenjobs queue
        _dispatchTask(task)

        # Clear out old jobs
        self.deleteUntil(datetime.now() - timedelta(hours=24))

        return records

    security.declareProtected(ZEN_ADD, 'addJob')
    def addJob(self, jobclass,
            description=None, args=None, kwargs=None, properties=None):
        """
        Schedule a new L{Job} from the class specified.

        NOTE: The job WILL NOT run until you commit the transaction!

        @return: An JobRecord object that can be used to check on the job
        results or abort the job
        @rtype: L{JobRecord}
        """
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Create the task ID here (tell Celery to use this ID)
        job_id = str(uuid4())

        # Retrieve the job instance
        job = current_app.tasks[jobclass.name]

        # Create a job record
        jobrecord = self._savejobrecord(
                job_id, job, description, args, kwargs, **properties
            )

        # Dispatch job to zenjobs queue
        _dispatchTask(job, args=args, kwargs=kwargs, task_id=job_id)

        # Clear out old jobs
        self.deleteUntil(datetime.now() - timedelta(hours=24))

        return jobrecord

    def _savejobrecord(self, job_id, job, desc, args, kwargs, **properties):
        # Put a pending job in the database. zenjobs will wait to run this
        # job until it exists.
        try:
            desc = desc if desc else job.getJobDescription(*args, **kwargs)
        except Exception:
            desc = "%s(%s, %s)" % (job.name, args, kwargs)

        user = getSecurityManager().getUser()
        if not isinstance(user, basestring):
            user = user.getId()

        # Add job metadata to the database
        meta = JobRecord(
                id=job_id,
                user=user,
                job_name=job.name,
                job_type=job.getJobType(),
                job_description=desc,
                date_scheduled=datetime.utcnow(),
            )
        for prop, propval in properties.iteritems():
            setattr(meta, prop, propval)
        self._setOb(job_id, meta)
        jobrecord = self._getOb(job_id)
        self.getCatalog().catalog_object(jobrecord)
        log.info("Created job %s: %s", job, jobrecord.id)
        return jobrecord

    def wait(self, job_id):
        return self.getJob(job_id).wait()

    def update(self, job_id, **kwargs):
        log.debug("Updating job %s with %s", job_id, kwargs)
        jobrecord = self.getJob(job_id)
        jobrecord.update(kwargs)
        self.getCatalog().catalog_object(jobrecord)

    def getJob(self, jobid):
        """
        Return a L{JobRecord} object that matches the id specified.

        @param jobid: id of the L{JobRecord}.
        @type jobid: str
        @return: A matching L{JobRecord} object,
            or raises a NoSuchJobException if none is found
        @rtype: L{JobRecord}, None
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

    security.declareProtected(ZEN_MANAGE_DMD, 'deleteUntil')
    def deleteUntil(self, untiltime):
        """
        Delete all jobs older than untiltime.
        """
        return
        for b in self.getCatalog()()[:]:
            try:
                ob = b.getObject()
                if ob.finished != None and ob.finished < untiltime:
                    self.deleteJob(ob.getId())
                elif ob.status == states.ABORTED and (ob.started is None or ob.started < untiltime):
                    self.deleteJob(ob.getId())
            except ConflictError:
                pass

    security.declareProtected(ZEN_MANAGE_DMD, 'clearJobs')
    def clearJobs(self):
        """
        Clear out all finished jobs.
        """
        for b in self.getCatalog()():
            self.deleteJob(b.getObject().getId())

    security.declareProtected(ZEN_MANAGE_DMD, 'killRunning')
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


InitializeClass(JobManager)
