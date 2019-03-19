##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import transaction
import uuid

from celery import states, chain

from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD
from Products.ZenModel.ZenModelRM import ZenModelRM

from .exceptions import NoSuchJobException
from .utils.accesscontrol import ZClassSecurityInfo, ZInitializeClass
from .zenjobs import app

log = logging.getLogger("zen.JobManager")


def manage_addJobManager(context, oid="JobManager"):
    """Add the JobManager class to dmd."""
    jm = JobManager(oid)
    context._setObject(oid, jm)
    return getattr(context, oid)


@ZInitializeClass
class JobManager(ZenModelRM):
    """Manages Jobs."""

    security = ZClassSecurityInfo()
    meta_type = portal_type = "JobManager"

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

        NOTE: The jobs will not start until you commit the transaction.

        :param joblist: task signatures as positional arguments
        :type joblist: celery.canvas.Signature
        :param options: additional options/settings to apply to each job
        :type options: keyword/value arguments, str=Any
        :return: The task signatures.
        :rtype: Tuple[Signature]
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
        return tuple(signatures)

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

        :return: The job ID
        :rtype: str
        """
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Retrieve the job instance
        task = app.tasks[jobclass.name]
        if task is None:
            raise NoSuchJobException("No such job '%s'" % jobclass.name)

        if description is not None:
            properties["description"] = description

        # Retrieve the job instance
        task = app.tasks[jobclass.name]
        if task is None:
            raise NoSuchJobException("No such job '%s'" % jobclass.name)

        task_id = str(uuid.uuid4())
        # Build the signature to call the task
        s = task.s(*args, **kwargs).set(**properties).set(task_id=task_id)

        # Dispatch job to zenjobs queue
        hook = _SendTask(s)
        transaction.get().addAfterCommitHook(hook)
        return task_id

    def wait(self, jobid):
        """Wait for the job identified by job_id to complete.

        :param str jobid: The ID of the job.
        """
        return

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
            status, userid

        Sort arguments:
            key, reverse, offset, limit

        :rtype: {Dict[jobs:Sequence[JobRecord], total:Int]}
        """
        return {"jobs": (), "total": 0}

    def update(self, jobid, **kwargs):
        """Update the jobrecord identified by job_id with the given values.

        :param str jobid: The ID of the job.
        """
        pass

    def getJob(self, jobid):
        """Return information about the job identified by jobid.

        :param str jobid: The ID of the job.
        """
        raise NoSuchJobException(jobid)

    def deleteJob(self, jobid):
        """Delete the job.

        :param str jobid: The ID of the job.
        """
        return

    def _getByStatus(self, statuses, jobtype=None):
        return iter(())

    def getUnfinishedJobs(self, type_=None):
        """Return jobs that are not completed.

        Includes jobs that have not started.

        :return: All jobs in the requested state.
        :rtype: generator
        """
        return self._getByStatus(states.UNREADY_STATES, type_)

    def getRunningJobs(self, type_=None):
        """Return the jobs that have started but not not finished.

        :return: All jobs in the requested state.
        :rtype: generator
        """
        return self._getByStatus((states.STARTED, states.RETRY), type_)

    def getPendingJobs(self, type_=None):
        """Return the jobs that have not yet started.

        :return: All jobs in the requested state.
        :rtype: generator
        """
        return self._getByStatus((states.RECEIVED, states.PENDING), type_)

    def getFinishedJobs(self, type_=None):
        """Return the jobs that have finished.

        :return: All jobs in the requested state.
        :rtype: generator
        """
        return self._getByStatus(states.READY_STATES, type_)

    def getAllJobs(self, type_=None):
        """Return all jobs.

        :return: All jobs in the requested state.
        :rtype: generator
        """
        return self._getByStatus(states.ALL_STATES, type_)

    @security.protected(ZEN_MANAGE_DMD)
    def clearJobs(self):
        """Clear out all finished jobs."""
        pass

    @security.protected(ZEN_MANAGE_DMD)
    def killRunning(self):
        """Abort running jobs."""
        pass


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
