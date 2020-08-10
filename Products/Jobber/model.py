##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import os
import time

from celery import states
from celery.contrib.abortable import ABORTED
from zope.component import getUtility
from zope.interface import implementer

from Products.Zuul.interfaces import IMarshaller, IMarshallable

from .config import ZenJobs
from .interfaces import IJobStore, IJobRecord
from .storage import Fields
from .utils.log import inject_logger
from .zenjobs import app

mlog = logging.getLogger("zen.zenjobs.model")


@implementer(IJobRecord, IMarshallable)
class JobRecord(object):
    """Zenoss-centric record of a job submitted to ZenJobs."""

    __slots__ = tuple(key for key in Fields.keys())

    @classmethod
    def make(cls, data):
        if not (data.viewkeys() <= Fields.viewkeys()):
            bad = data.viewkeys() ^ Fields.viewkeys()
            raise AttributeError(
                "Jobrecord does not have attribute%s %s" % (
                    "" if len(bad) == 1 else "s",
                    ", ".join("'%s'" % v for v in bad),
                ),
            )
        record = cls()
        for k, v in data.viewitems():
            setattr(record, k, v)
        return record

    def __getattr__(self, name):
        # Clever hack for backward compatibility.
        # Users of JobRecord added arbitrary attributes.
        if name not in self.__slots__:
            details = getattr(self, "details", {}) or {}
            if name not in details:
                raise AttributeError(name)
            return details[name]
        return None

    @property
    def __dict__(self):
        # Clever hack for backward compatibility.
        # Some uses of JobRecord iterated over the '__dict__' attribute
        # to retrieve job-specific/custom attributes.
        base = {
            k: getattr(self, k)
            for k in self.__slots__ + ("uuid", "duration", "complete")
            if k != "details"
        }
        details = getattr(self, "details", {}) or {}
        base.update(**details)
        return base

    @property
    def uuid(self):
        """Alias for jobid.

        This property exists for compatiblity reasons.
        """
        return self.jobid

    @property
    def duration(self):
        if self.status in (states.PENDING, states.RECEIVED):
            return None
        if self.complete:
            return self.finished - self.started
        return time.time() - self.started

    @property
    def complete(self):
        return self.status in states.READY_STATES

    def abort(self):
        """Abort the job."""
        return self.result.abort()

    def wait(self):
        return self.result.wait()

    @property
    def result(self):
        return app.tasks[self.name].AsyncResult(self.jobid)


@implementer(IMarshaller)
class JobRecordMarshaller(object):
    """Serializes JobRecord objects into dictionaries."""

    _default_keys = (
        "jobid",
        "summary",
        "description",
        "created",
        "started",
        "finished",
        "status",
        "userid",
    )

    # Maps legacy job record field names to their new field names.
    _key_map = {
        "uuid": "jobid",
        "scheduled": "created",
        "user": "userid",
    }

    def __init__(self, obj):
        """Initialize a JobRecordMarshaller object.

        :param JobRecord obj: The object to marshall
        """
        self.__obj = obj

    def marshal(self, keys=None):
        """Returns a dict containing the JobRecord's data.
        """
        fields = self._default_keys if keys is None else keys
        return {name: self._get_value(name) for name in fields}

    def _get_value(self, name):
        key = self._key_map.get(name, default=name)
        return getattr(self.__obj, key, None)


@inject_logger(log=mlog)
def save_jobrecord(log, body=None, headers=None, properties=None, **ignored):
    """Save the Zenoss specific job metadata to redis.

    This function is registered as a handler for the before_task_publish
    signal.  Right before the task is published to the queue, this function
    is invoked with the data to be published to the queue.

    :param dict body: Task data
    :param dict headers: Headers to accompany message sent to Celery worker
    :param dict properties: Additional task and custom key/value pairs
    """
    if not body:
        # If body is empty (or None), no job to save.
        log.info("no body, so no job")
        return

    if headers is None:
        # If headers is None, bad signal so ignore.
        log.info("no headers, bad signal?")
        return

    # Make sure properties is not None
    properties = dict(properties) if properties else {}

    # Retrieve the job storage connection.
    storage = getUtility(IJobStore, "redis")

    # Retrieve the job ID  (same as task ID)
    jobid = body.get("id")

    userid = headers.get("userid")
    if userid is None:
        log.warn("No user ID submitted with job %s", jobid)

    properties.update({
        "status": states.PENDING,
        "created": time.time(),
    })
    if userid:
        properties["userid"] = userid

    if jobid not in storage:
        taskname = body.get("task")
        task = app.tasks[taskname]
        record = build_redis_record(
            task,
            body.get("id"),
            body.get("args", ()),
            body.get("kwargs", {}),
            **properties
        )
        storage[record["jobid"]] = record
        log.info("Saved record for job %s", jobid)
    else:
        log.info("Record already exists for job %s", jobid)


def build_redis_record(
    task, jobid, args, kwargs,
    description=None, status=None, created=None, userid=None, details=None,
    **ignored
):
    if not jobid:
        raise ValueError("Invalid job ID: '%s'" % (jobid,))
    if not description:
        description = task.description_from(*args, **kwargs)
    record = {
        "jobid": jobid,
        "name": task.name,
        "summary": task.summary,
        "description": description,
        "logfile": os.path.join(ZenJobs.get("job-log-path"), "%s.log" % jobid),
    }
    if status:
        record["status"] = status
    if created:
        record["created"] = created
    if userid:
        record["userid"] = userid
    if details:
        record["details"] = details
    return record


@inject_logger(log=mlog)
def update_job_status(log, task_id=None, task=None, **kwargs):
    """Update the job record's state."""
    jobstore = getUtility(IJobStore, "redis")
    if task_id not in jobstore:
        return
    job_status = jobstore.getfield(task_id, "status")
    task_status = app.backend.get_status(task_id)
    log.debug("task_status %s  job_status %s", task_status, job_status)
    if ABORTED in (job_status, task_status):
        task_status = job_status = ABORTED
    if task_status in states.READY_STATES:
        tmfield = "finished"
        job_status = task_status
    else:
        tmfield = "started"
        job_status = states.STARTED
    tmvalue = time.time()
    jobstore.update(task_id, **{"status": job_status, tmfield: tmvalue})
    log.debug("status %s, %s: %s", job_status, tmfield, tmvalue)
