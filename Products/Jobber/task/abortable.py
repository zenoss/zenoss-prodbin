##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os
import signal
import sys
import thread
import threading

from celery import states
from celery.app import push_current_task, pop_current_task
from celery.exceptions import Ignore
from celery.contrib.abortable import (
    AbortableTask, AbortableAsyncResult, ABORTED,
)
from zope.component import getUtility

from Products.ZenUtils.Threading import inject_exception_into_thread

from ..exceptions import JobAborted, TaskAborted
from ..interfaces import IJobStore


class AbortableResult(AbortableAsyncResult):
    """The result of an Abortable."""

    def abort(self):
        """Abort the job."""
        jobstore = getUtility(IJobStore, "redis")
        jobstore.update(self.id, status=ABORTED)
        return super(AbortableResult, self).abort()


class Abortable(AbortableTask):
    """A task that can be aborted."""

    abstract = True
    throws = (TaskAborted,)

    def AsyncResult(self, task_id):
        """Return the accompanying AbortableResult instance."""
        return AbortableResult(task_id, backend=self.backend)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        result = super(Abortable, self).on_failure(
            exc, task_id, args, kwargs, einfo,
        )
        # If the exception is TaskAborted, change the status to ABORTED
        # because Celery always marks jobs that raise an exception as FAILURE.
        if isinstance(exc, TaskAborted):
            result = self.AsyncResult(task_id)
            result.backend.store_result(
                task_id, result=None, status=states.ABORTED, traceback=None,
            )
            self.log.debug(
                "On TaskAborted exception, reset the task status to ABORTED",
            )

        return result

    def __call__(self, *args, **kwargs):
        """Execute the task."""
        # Ignore this task if it's already aborted.
        jobstore = getUtility(IJobStore, "redis")
        status = jobstore.getfield(self.request.id, "status")
        if status == ABORTED:
            self.log.info("Ignoring aborted job: %s", self.request.id)
            raise Ignore()
        try:
            self._run, self.run = self.run, self._exec
            return super(Abortable, self).__call__(*args, **kwargs)
        finally:
            self.run = self._run

    def _exec(self, *args, **kwargs):
        if self.request.id is None:
            self.log.error("task has no ID")
            return
        aborter = _TaskAborter(self, thread.get_ident())
        try:
            aborter.start()
            self.log.info("Job started")
            result = self._run(*args, **kwargs)
        except Exception as ex:
            self.log.error("Job failed: %r", ex)
            raise
        except JobAborted:
            self.log.warning("Job aborted")
            # Convert JobAborted into TaskAborted.
            # JobAborted is derived from BaseException and TaskAborted
            # is derviced from Exception.  Raising TaskAborted will result
            # in desired behavior from Celery.  Re-raising JobAborted will
            # cause the Celery worker process to exit.
            cls, instance, tb = sys.exc_info()[0:3]
            raise TaskAborted, TaskAborted(), tb
        else:
            self.log.info("Job finished")
            return result
        finally:
            aborter.stop.set()
            aborter.join()
            self.log.debug("Stopped the ABORTED status monitor thread")


class _TaskAborter(threading.Thread):

    def __init__(self, task, tid):
        self.task = task
        self.tid = tid
        self.request = task.request
        self.task_id = self.request.id
        self.log = self.task.log
        self.stop = threading.Event()
        super(_TaskAborter, self).__init__(name="_TaskAborter")

    def run(self):
        try:
            # Push the request and task to their respective
            # thread-local stacks.
            self.task.request_stack.push(self.request)
            push_current_task(self.task)
            result = self.task.AsyncResult(self.task_id)
            while True:
                if self._job_aborted(result):
                    break
                if self._stopped():
                    break
            if not self.stop.wait(5.0):
                self.log.warning("Forcing worker process to exit")
                os.kill(os.getpid(), signal.SIGKILL)
        finally:
            # Pop the request and task from their respective
            # thread-local stacks
            pop_current_task()
            self.task.request_stack.pop()

    def _stopped(self):
        if not self.stop.wait(0.1):
            return False
        self.log.debug("Stopping ABORTED status monitor thread")
        return True

    def _job_aborted(self, result):
        if not result.is_aborted():
            return False
        self.log.warning("Aborting job")
        inject_exception_into_thread(self.tid, JobAborted)
        self.log.debug("Injected the JobAbort exception")
        return True
