##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from celery import Task
from AccessControl.SecurityManagement import getSecurityManager

from ..utils.log import get_task_logger

_default_summary = "Task {0.__class__.__name__}"


class ZenTask(Task):
    """Base class for tasks."""

    abstract = True
    description_template = None
    summary = None

    def __new__(cls, *args, **kwargs):
        task = super(ZenTask, cls).__new__(cls, *args, **kwargs)
        summary = getattr(task, "summary", None)
        if not summary:
            summary = _default_summary.format(task)
        setattr(cls, "summary", summary)
        return task

    @classmethod
    def description_from(cls, *args, **kwargs):
        if not cls.description_template:
            return cls.summary
        return cls.description_template.format(*args, **kwargs)

    @property
    def log(self):
        """Return the logger for this job."""
        return get_task_logger(self.name)

    @property
    def description(self):
        """Return a description of the task."""
        if not hasattr(self, "request_stack"):
            return self.summary
        req = self.request
        args = req.args if req.args else ()
        kw = req.kwargs if req.kwargs else {}
        return type(self).description_from(*args, **kw)

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
        # If debug logging is enabled, log the traceback.
        if einfo.type in getattr(self, "throws", ()) \
                and self.log.isEnabledFor(logging.DEBUG):
            self.log.error(einfo.traceback)

        return result
