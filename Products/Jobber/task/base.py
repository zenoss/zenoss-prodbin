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

from celery import Task
from AccessControl.SecurityManagement import getSecurityManager
from zope.component import getUtility

import Products.ZenUtils.guid as guid

from Products.ZenEvents import Event
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher

from ..exceptions import TaskAborted
from ..utils.log import get_task_logger

_default_summary = "Task {0.__class__.__name__}"


class ZenTask(Task):
    """Base class for tasks."""

    abstract = True
    description_template = None
    summary = None

    def __new__(cls, *args, **kwargs):
        task = super(ZenTask, cls).__new__(cls, *args, **kwargs)
        if cls.summary is None:
            cls.summary = _default_summary.format(task)
        if cls.description_template is None:
            cls.description_template = cls.summary
        return task

    @property
    def log(self):
        """Return the logger for this job."""
        return get_task_logger(self.name)

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """Return the description of the task instance.

        The returned string is typically a render of description_template,
        e.g.

            description_template.format(*args, **kwargs)

        where args and kwargs are the arguments to the task.
        """
        return cls.description_template.format(*args, **kwargs)

    def subtask(self, *args, **kw):
        """Return celery.signature object for this task.

        This overridden version adds the currently logged in user's ID
        to the headers sent along with the task to Celery.
        """
        headers = kw.setdefault("headers", {})
        userid = getSecurityManager().getUser().getId()
        headers["userid"] = userid
        return super(ZenTask, self).subtask(*args, **kw)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        result = super(ZenTask, self).on_failure(
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

        # If debug logging is enabled, log the traceback.
        if einfo.type in getattr(self, "throws", ()) \
                and self.log.isEnabledFor(logging.DEBUG):
            self.log.error(einfo.traceback)

        return result
