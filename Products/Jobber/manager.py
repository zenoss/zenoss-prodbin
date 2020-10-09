##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os
import transaction
import uuid

from celery import states, chain
from zope.component import getUtility

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD

from .exceptions import NoSuchJobException
from .interfaces import IJobStore
from .model import LegacySupport, JobRecord, RedisRecord, sortable_keys
from .utils.accesscontrol import ZClassSecurityInfo, ZInitializeClass
from .zenjobs import app

log = logging.getLogger("zen.zenjobs.JobManager")

JOBMANAGER_VERSION = 2


def manage_addJobManager(context, oid="JobManager"):
    """Add the JobManager class to dmd."""
    jm = JobManager(oid)
    context._setObject(oid, jm)
    return getattr(context, oid)


@ZInitializeClass
class JobManager(ZenModelRM):
    """Manages Jobs."""

    # Attribute that allows a migration script to determine whether this
    # object should be replaced.
    _jobmanager_version = None

    security = ZClassSecurityInfo()
    meta_type = portal_type = "JobManager"

    def __init__(self, *args, **kw):
        ZenModelRM.__init__(self, *args, **kw)
        self._jobmanager_version = JOBMANAGER_VERSION

    @security.protected(ZEN_MANAGE_DMD)
    def addJobChain(self, *joblist, **options):
        """Submit a list of Signature objects that will execute in list order.

        If options are specified, they are applied to each subjob; options
        that were specified directly on the subjob are not overridden.

        Supported options include:
            immutable {bool} Set True to 'freeze' the job arguments.
            ignoreresult {bool} Set True to drop the result of the jobs.

        If both options are not set, they default to False, which means the
        result of the prior job is passed to the next job as argument(s).

        NOTE: The jobs WILL NOT run until the current transaction is committed!

        :param joblist: task signatures as positional arguments
        :type joblist: Tuple[celery.canvas.Signature]
        :param options: additional options/settings to apply to each job
        :type options: Dict[str, Any]
        :return: The job record objects associated with the jobs.
        :rtype: Tuple[JobRecord]
        """
        signatures = []
        for signature in joblist:
            task_id = str(uuid.uuid4())
            signature = signature.set(**options).set(task_id=task_id)
            signatures.append(signature)
        job = chain(*signatures)

        # Defer sending the job until the transaction has been committed.
        send = _SendTask(job)
        transaction.get().addAfterCommitHook(send)
        return tuple(
            JobRecord.make(RedisRecord.from_signature(s))
            for s in signatures
        )

    @security.protected(ZEN_MANAGE_DMD)
    def addJob(
        self,
        jobclass,
        description=None,
        args=None,
        kwargs=None,
        properties=None,
    ):
        """Schedule a new job for execution.

        NOTE: The job WILL NOT run until the current transaction is committed!

        :type jobclass: Task
        :type description: Union[str, None]
        :type args: Union[Sequence[Any], None]
        :type kwargs: Union[Mapping[str, Any], None]
        :type properties: Union[Mapping[str, Any], None]
        :return: The job record of the submitted job
        :rtype: JobRecord
        """
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Retrieve the task object
        task = app.tasks.get(jobclass.name)
        if task is None:
            raise NoSuchJobException("No such job '%s'" % jobclass.name)

        if description is not None:
            properties["description"] = description

        task_id = str(uuid.uuid4())
        # Build the signature to call the task
        s = task.s(*args, **kwargs).set(**properties).set(task_id=task_id)

        # Dispatch the task
        result = s.apply_async()
        log.debug("Submitted job to zenjobs  job=%s id=%s", s.task, result.id)

        return JobRecord.make(RedisRecord.from_signature(s))

    def wait(self, jobid):
        """Wait for the job identified by jobid to complete.

        :param str jobid: The ID of the job.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        taskname = storage.getfield(jobid, "name")
        app.tasks.get(taskname).AsyncResult(jobid).wait()

    def query(
        self,
        criteria=None,
        key="created",
        reverse=False,
        offset=0,
        limit=None,
    ):
        """Return jobs matching the provided criteria.

        Criteria fields:
            status - Select only records with this status
            user/userid - Select only records with this user ID

        Sort arguments:
            key - Result is sorted by this field
            reverse - True to reverse the sort order
            offset - The returned result starts with this index
            limit - Maximum number of returned records.

        Supported values for 'key':
            jobid
            name
            summary
            description
            userid
            logfile
            created
            started
            finished
            status
            uuid
            scheduled
            user

        :type criteria: Mapping[str, Union[int, float, str]]
        :type key: str
        :type reverse: boolean
        :type offset: int
        :type limit: Union[int, None]
        :rtype: {"jobs": Tuple[JobRecord], "total": int}
        """
        criteria = criteria if criteria is not None else {}
        normalized_criteria = {
            LegacySupport.from_key(k): criteria[k] for k in criteria
        }
        valid = ["status", "userid"]
        invalid_fields = set(normalized_criteria.keys()) - set(valid)
        if invalid_fields:
            raise ValueError(
                "Invalid criteria field: %s" % ", ".join(invalid_fields),
            )
        normalized_key = LegacySupport.from_key(key)
        if normalized_key not in sortable_keys:
            raise ValueError("Invalid sort key: %s" % (key,))
        try:
            storage = getUtility(IJobStore, "redis")
            if len(normalized_criteria):
                jobids = storage.search(**normalized_criteria)
                jobdata = storage.mget(*jobids)
            else:
                jobdata = storage.values()
            result = sorted(
                jobdata,
                key=lambda x: x[normalized_key],
                reverse=reverse,
            )
            end = len(result) if limit is None else offset + limit
            jobs = tuple(
                JobRecord.make(jobdata) for jobdata in result[offset:end]
            )
            return {"jobs": jobs, "total": len(result)}
        except Exception:
            log.exception("Internal Error")
            return {"jobs": (), "total": 0}

    def update(self, jobid, **kwargs):
        """Add or update job specific properties.

        :param str jobid: The ID of the job.
        :param **kwargs: The job-specific properties.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        storage.update(jobid, details=kwargs)

    def getJob(self, jobid):
        """Return the job identified by jobid.

        If no job exists with the given ID, a NoSuchJobException is raised.

        :param str jobid: The ID of the job.
        :rtype: JobRecord
        :raises NoSuchJobException: If jobid doesn't exist.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        return JobRecord.make(storage[jobid])

    @security.protected(ZEN_MANAGE_DMD)
    def deleteJob(self, jobid):
        """Delete the job data identified by jobid.

        :param str jobid: The ID of the job to delete.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            log.warn("Cannot delete job that does not exist: %s", jobid)
            return
        job = storage[jobid]
        if job.get("status") not in states.READY_STATES:
            task = app.tasks[job["name"]]
            result = task.AsyncResult(jobid)
            result.abort()
        # Clean up the log file
        logfile = job.get("logfile")
        if logfile is not None:
            try:
                os.remove(logfile)
            except (OSError, IOError):
                # Did our best!
                pass
        del storage[jobid]
        log.info("Job deleted  jobid=%s name=%s", jobid, job["name"])

    def getUnfinishedJobs(self, type_=None):
        """Return jobs that are not completed.

        Includes jobs that have not started.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType(states.UNREADY_STATES, type_)

    def getRunningJobs(self, type_=None):
        """Return the jobs that have started but not not finished.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType((states.STARTED, states.RETRY), type_)

    def getPendingJobs(self, type_=None):
        """Return the jobs that have not yet started.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType((states.RECEIVED, states.PENDING), type_)

    def getFinishedJobs(self, type_=None):
        """Return the jobs that have finished.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType(states.READY_STATES, type_)

    def getAllJobs(self, type_=None):
        """Return all jobs.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        storage = getUtility(IJobStore, "redis")
        if type_ is not None:
            jobtype = _getJobTypeStr(type_)
            jobids = storage.search(name=jobtype)
            result = storage.mget(*jobids)
        else:
            result = storage.values()
        return (JobRecord.make(jd) for jd in result)

    @security.protected(ZEN_MANAGE_DMD)
    def clearJobs(self):
        """Delete all finished jobs."""
        storage = getUtility(IJobStore, "redis")
        jobids = tuple(storage.search(status=states.READY_STATES))
        logfiles = (
            storage.getfield(j, "logfile")
            for j in jobids
        )
        for logfile in (lf for lf in logfiles if lf is not None):
            if os.path.exists(logfile):
                try:
                    os.remove(logfile)
                except (OSError, IOError):
                    pass
        storage.mdelete(*jobids)

    @security.protected(ZEN_MANAGE_DMD)
    def killRunning(self):
        """Abort running jobs."""
        for job in self.getUnfinishedJobs():
            job.abort()


class _SendTask(object):
    """Sends the task to Celery when invoked."""

    def __init__(self, signature):
        self.__s = signature

    def __call__(self, status, **kw):
        if status:
            result = self.__s.apply_async()
            log.debug(
                "Submitted job to zenjobs  job=%s id=%s",
                self.__s.task, result.id,
            )
        else:
            log.debug("Job discarded  job=%s", self.__s.task)


def _getByStatusAndType(statuses, jobtype=None):
    fields = {"status": statuses}
    if jobtype is not None:
        fields["name"] = _getJobTypeStr(jobtype)
    storage = getUtility(IJobStore, "redis")
    jobids = storage.search(**fields)
    result = storage.mget(*jobids)
    return (JobRecord.make(jobdata) for jobdata in result)


def _getJobTypeStr(jobtype):
    if isinstance(jobtype, type):
        return jobtype.name
    task = app.tasks.get(str(jobtype))
    if not task:
        raise ValueError("No such job: {!r}".format(jobtype))
    return task.name
