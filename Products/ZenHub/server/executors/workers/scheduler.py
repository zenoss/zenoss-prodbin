##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from functools import partial

from twisted.internet import defer
from twisted.internet.task import deferLater

from .dispatcher import TaskDispatcher


class Scheduler(object):
    """
    Schedule tasks for execution.
    """

    def __init__(self, clock, name, worklist, pool, log):
        self.clock = clock
        self.name = name
        self.worklist = worklist
        self.workers = pool
        self.log = log

    @defer.inlineCallbacks
    def __call__(self):
        """
        Schedule tasks for execution by workers.
        """
        worker = None
        try:
            # Retrieve a task from the work queue
            task = yield self.worklist.pop()

            # Retrieve a worker to execute the task.
            worker = yield self.workers.hire()
            self.log.info(
                "hired worker for task  "
                "worker=%s collector=%s service=%s method=%s id=%s",
                worker.name,
                task.call.monitor,
                task.call.service,
                task.call.method,
                task.call.id,
            )

            # Schedule the worker to execute the task
            dispatcher = TaskDispatcher(worker, task, self.log)
            deferLater(self.clock, 0, dispatcher).addBoth(
                partial(self._task_done, worker, task)
            )
        except Exception:
            self.log.exception("unexpected failure  worklist=%s", self.name)
            # Layoff the worker (if a worker was hired)
            if worker:
                self.workers.layoff(worker)

    def _task_done(self, worker, task, *args):
        # self.log.info("[_task_done] args -> %s", args)
        # self.log.info("[_task_done] task.error -> %s", task.error)
        if task.retryable:
            self.worklist.pushfront(task.priority, task)
            self.log.info(
                "enqueued task for retry  "
                "collector=%s service=%s method=%s id=%s",
                task.call.monitor,
                task.call.service,
                task.call.method,
                task.call.id.hex,
            )
        self.workers.layoff(worker)
        self.log.info("worker ready for next task  worker=%s", worker.name)
