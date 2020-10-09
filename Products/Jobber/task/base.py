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
import time

from AccessControl.SecurityManagement import getSecurityManager
from celery import Task, states
from celery.exceptions import Ignore, SoftTimeLimitExceeded

from .event import SendZenossEventMixin
from .utils import job_log_has_errors
from ..utils.log import get_task_logger, get_logger

_default_summary = "Task {0.__class__.__name__}"

mlog = get_logger("zen.zenjobs.task.base")


class ZenTask(SendZenossEventMixin, Task):
    """Base class for tasks."""

    abstract = True
    description_template = None
    summary = None

    throws = (SoftTimeLimitExceeded,)

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

    def after_return(self, status, retval, task_id, args, kwargs, eninfo):
        if status == states.SUCCESS and job_log_has_errors(task_id):
            status = states.FAILURE
            self.update_state(state=status)
        return super(ZenTask, self).after_return(
            status, retval, task_id, args, kwargs, eninfo,
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        result = super(ZenTask, self).on_failure(
            exc, task_id, args, kwargs, einfo,
        )
        if (
            einfo.type in getattr(self, "throws", ())
            and not self.log.isEnabledFor(logging.DEBUG)
        ):
            # Log a simple message for known exceptions when not DEBUG.
            self.log.error("Job failed: %r", exc)
        else:
            # log the traceback for everything else.
            self.log.error("Job failed: %r\n%s", exc, einfo.traceback)

        # Always log errors for the main logger
        mlog.error("Job failed: %r", exc)

        return result

    def __call__(self, *args, **kwargs):
        """Execute the task."""
        self.__run, self.run = self.run, self.__exec
        try:
            return super(ZenTask, self).__call__(*args, **kwargs)
        finally:
            self.run = self.__run
            del self.__run

    def __exec(self, *args, **kwargs):
        if self.request.id is None:
            self.log.error("task has no ID")
            raise Ignore()
        started_mesg = "Job started"
        finished_mesg = "Job finished  duration=%0.3f"
        self.log.info(started_mesg)
        mlog.debug(started_mesg)
        start = time.time()
        result = self.__run(*args, **kwargs)
        stop = time.time()
        mlog.debug(finished_mesg, stop - start)
        self.log.info(finished_mesg, stop - start)
        return result
