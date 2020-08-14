##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import six

from zope.component import getUtility

import Products.ZenUtils.guid as guid

from Products.ZenEvents import Event
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher

from ..config import ZenJobs
from ..exceptions import NoSuchJobException, TaskAborted
from ..task import Abortable, DMD, ZenTask
from ..zenjobs import app

_MARKER = object()


class Job(Abortable, DMD, ZenTask):
    """Base class for legacy jobs."""

    abstract = True  # Job class itself is not registered.

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job.

        By default, the class type name is returned.
        """
        return cls.name

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """Return the description of the task instance."""
        raise NotImplementedError

    @classmethod
    def description_from(cls, *args, **kwargs):
        """Alias for getJobDescription."""
        return cls.getJobDescription(*args, **kwargs)

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """Return a celery.canvas.Signature instance.

        The Signature instance wraps the given job, its arguments, and options.
        """
        task = app.tasks.get(cls.name)
        if task is None:
            raise NoSuchJobException(
                "No job named '{}' is registered".format(cls.name),
            )
        args = args or ()
        kwargs = kwargs or {}
        # Build the task's call signature
        signature = task.s(*args, **kwargs).set(**options)
        # Add 'description' if given
        if description:
            signature = signature.set(description=description)
        return signature

    def __call__(self, *args, **kwargs):
        """Execute the job."""
        # Make the 'run' method an alias for the '_run' method, so
        # that legacy Job-based tasks match the celery.Task API.
        self.run = self._run
        return super(Job, self).__call__(*args, **kwargs)

    def setProperties(self, **properties):
        jobid = self.request.id
        if not jobid:
            return
        record = self.dmd.JobManager.getJob(jobid)
        details = record.details or {}
        details.update(**properties)
        self.dmd.JobManager.update(jobid, **details)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            result = super(Job, self).on_failure(
                exc, task_id, args, kwargs, einfo,
            )
            # Don't send an event when a job is aborted.
            if not isinstance(exc, TaskAborted):
                # Send an event about the job failure.
                publisher = getUtility(IEventPublisher)
                event = Event.buildEventFromDict({
                    "device": self.getJobType(),
                    "severity": Event.Error,
                    "component": "zenjobs",
                    "eventClass": "/App/Job/Fail",
                    "message": self.getJobDescription(*args, **kwargs),
                    "summary": repr(exc),
                    "jobid": str(task_id),
                })
                event.evid = guid.generate(1)
                publisher.publish(event)

            return result
        except Exception:
            self.log.exception("Internal Error")

    def _get_config(self, key, default=_MARKER):
        value = ZenJobs.get(key, default=default)
        if value is _MARKER:
            raise KeyError("Config option '{}' is not defined".format(key))
        return value

    def _run(self, *args, **kw):
        raise NotImplementedError(
            "Not implemented: {0.__class__.__name__}._run".format(self),
        )
