##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

from twisted.internet import defer
from twisted.spread import pb, banana, jelly
from zope.component import getUtility

from Products.ZenHub.PBDaemon import RemoteException

from ..interface import IHubServerConfig
from ..priority import servicecall_priority_map
from ..utils import UNSPECIFIED as _UNSPECIFIED, getLogger

_InternalErrors = (
    pb.ProtocolError, banana.BananaError, jelly.InsecureJelly,
)
_RemoteErrors = (RemoteException, pb.RemoteError)


class WorkerPoolExecutor(object):
    """An executor that executes service calls using remote workers."""

    def __init__(self, name, worklist, pool, monitor):
        """Initialize a WorkerPoolExecutor instance."""
        self.__name = name
        self.__worklist = worklist
        self.__workers = pool
        self.__log = getLogger(self)
        self.__states = {
            "running": _Running(name, worklist, pool, monitor, self.__log),
            "stopped": _Stopped(),
        }
        self.__state = self.__states["stopped"]

    @property
    def name(self):
        """Return the name of this executor."""
        return self.__name

    @property
    def pool(self):
        """Return the pool of workers available to this executor."""
        return self.__workers

    def start(self, reactor):
        """Start the executor."""
        self.__state = self.__states["running"]
        self.__state.start(reactor)

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        return self.__state.submit(call)

    def __repr__(self):
        return "<{0.__class__.__name__} '{1}'>".format(self, self.__name)


class _Stopped(object):
    """WorkerPoolExecutor in stopped state."""

    def submit(self, call):
        return defer.fail(pb.Error("ZenHub not ready."))


class _Running(object):
    """WorkerPoolExecutor in running state."""

    def __init__(self, name, worklist, pool, monitor, log):
        self.name = name
        self.worklist = worklist
        self.workers = pool
        self.monitor = monitor
        self.log = log
        config = getUtility(IHubServerConfig)
        self.task_max_retries = config.task_max_retries

    def start(self, reactor):
        self.reactor = reactor

    def submit(self, call):
        task = ServiceCallTask(self.name, call)
        task.received()
        self.monitor.handleReceived()
        self.worklist.push(task.priority, task)
        # Schedule a call to execute to process the new task.
        self.reactor.callLater(0, self.execute)
        self.log.info(
            "Received task service=%s method=%s id=%s",
            call.service, call.method, call.id.hex,
        )
        return task.deferred

    @defer.inlineCallbacks
    def execute(self):
        """Execute the next task in the worklist."""
        # If the worklist is empty, return as there's nothing to do.
        if not self.worklist:
            defer.returnValue(None)

        worker = None
        try:
            # Attempt to hire a worker.
            worker = yield self.workers.hire()

            # If no worker was hired, try again later.
            if worker is None:
                defer.returnValue(None)

            self.log.debug(
                "There are %s workers currently available to work %s tasks",
                self.workers.available + 1, len(self.worklist),
            )
            # Retrieve the next task
            task = self.worklist.pop()
            if task is None:
                defer.returnValue(None)
            try:
                # Notify listeners of a task execution attempt.
                self._handle_start(task, worker.workerId)

                # Run the task
                result = yield worker.run(task.call)

                # Task succeeded, process the result
                self._handle_success(task, result)
            except _RemoteErrors as ex:
                # These kinds of errors originate from the service and
                # are propagated directly back to the submitter.
                self._handle_failure(task, ex)
            except _InternalErrors as ex:
                # These are un-retryable errors that occur while attempting
                # to execute the call, so are logged and a summary error is
                # returned to the submitter.
                self.log.error(
                    "(%s) %s service=%s method=%s id=%s worker=%s",
                    type(ex), ex, task.call.service, task.call.method,
                    task.call.id, worker.workerId,
                )
                error = pb.Error((
                    "Internal ZenHub error: ({0.__class__.__name__}) {0}"
                    .format(ex)
                ).strip())
                self._handle_failure(task, error)
            except pb.PBConnectionLost as ex:
                # Lost connection to the worker; not a failure.
                # The attempt count is _not_ incremented.
                self.log.warn(
                    "Worker no longer accepting work worker=%s error=%s",
                    worker.workerId, ex,
                )
                self._handle_retry(task, ex)
            except Exception as ex:
                self._handle_error(task, ex)
                raise  # reraise to catch again in outer handler.
            finally:
                # if the task is retryable, push the task
                # to the front of its queue.
                if task.retryable:
                    self.worklist.pushfront(task.priority, task)
                    self.log.debug(
                        "Task queued for retry service=%s method=%s id=%s",
                        task.call.service, task.call.method, task.call.id.hex,
                    )
        except Exception as ex:
            # Unexpected exceptions caught here too.
            self.log.exception("Unexpected failure")
        finally:
            # Layoff the worker
            if worker:
                self.workers.layoff(worker)

            # If worklist contains a task, schedule another call to _execute.
            # However, introduce a 0.1 second delay to avoid maximizing CPU
            # utilization testing for a lack of available workers or logging
            # a recuring error with a task.
            if self.worklist:
                self.reactor.callLater(0.1, self.execute)

    def _handle_start(self, task, workerId):
        task.attempt += 1
        task.started(workerId)
        self.monitor.handleStarted(workerId, task.call)
        if task.attempt == 1:
            self._log_initial_start(task)
        else:
            self._log_subsequent_starts(task)

    def _handle_error(self, task, exception):
        if task.attempt >= self.task_max_retries:
            # No more attempts, handle the error as a failure.
            self.log.warn(
                "Retries exhausted service=%s method=%s id=%s",
                task.call.service, task.call.method, task.call.id.hex,
            )
            ex = pb.Error((
                "Internal ZenHub error: ({0.__class__.__name__}) {0}"
                .format(exception)
            ).strip())
            self._handle_failure(task, ex)
        else:
            # Still have attempts, handle the error as a retry.
            self._handle_retry(task, exception)

    def _handle_retry(self, task, exception):
        task.completed(retry=exception)
        self.monitor.handleCompleted(task.workerId, task.call)
        self._log_incomplete(task)

    def _handle_success(self, task, result):
        # Send the result back to the submitter
        self.reactor.callLater(0, task.success, result)
        # Notify listeners of call completion (and success)
        task.completed(result=result)
        self.monitor.handleCompleted(task.workerId, task.call)
        self._log_completed(task)

    def _handle_failure(self, task, exception):
        # Send failure back to the submitter
        self.reactor.callLater(0, task.failure, exception)
        # Notify listeners of call completion (and failure)
        task.completed(error=exception)
        self.monitor.handleCompleted(task.workerId, task.call)
        self._log_completed(task)

    def _log_initial_start(self, task):
        call = task.call
        waited = task.started_tm - task.received_tm
        self.log.info(
            "Begin task service=%s method=%s id=%s worker=%s waited=%0.2f",
            call.service, call.method, call.id.hex, task.workerId, waited,
        )

    def _log_subsequent_starts(self, task):
        call = task.call
        waited = task.started_tm - task.completed_tm
        self.log.info(
            "Retry task service=%s method=%s id=%s "
            "worker=%s attempt=%s waited=%0.2f",
            call.service, call.method, call.id.hex,
            task.workerId, task.attempt, waited,
        )

    def _log_incomplete(self, task):
        call = task.call
        elapsed = task.completed_tm - task.started_tm
        self.log.info(
            "Failed to complete task service=%s method=%s id=%s "
            "worker=%s duration=%0.2f error=%s",
            call.service, call.method, call.id.hex,
            task.workerId, elapsed, task.error,
        )

    def _log_completed(self, task):
        call = task.call
        elapsed = task.completed_tm - task.started_tm
        lifetime = task.completed_tm - task.received_tm
        status = "success" if not task.error else "failed"
        self.log.info(
            "Completed task service=%s method=%s id=%s "
            "worker=%s status=%s duration=%0.2f lifetime=%0.2f",
            call.service, call.method, call.id.hex,
            task.workerId, status, elapsed, lifetime,
        )


class ServiceCallTask(object):
    """Wraps a ServiceCall to track for use with WorkerPoolExecutor."""

    __slots__ = (
        "call", "deferred", "desc", "attempt", "priority",
        "received_tm", "started_tm", "completed_tm",
        "error", "retryable", "workerId",
    )

    def __init__(self, name, call):
        self.call = call
        self.deferred = defer.Deferred()
        self.desc = "%s:%s.%s" % (call.monitor, call.service, call.method)
        self.attempt = 0
        self.priority = servicecall_priority_map.get(
            (self.call.service, self.call.method),
        )
        self.received_tm = None
        self.started_tm = None
        self.completed_tm = None
        self.error = None
        self.retryable = True
        self.workerId = None

    def received(self):
        """Update task when receiving a call."""
        self.received_tm = time.time()

    def started(self, workerId):
        """Update task when starting a call."""
        self.started_tm = time.time()
        self.workerId = workerId

    def completed(
        self, result=_UNSPECIFIED, error=_UNSPECIFIED, retry=_UNSPECIFIED,
    ):
        """Update task when completing a call."""
        self.completed_tm = time.time()
        if result is not _UNSPECIFIED:
            self.error = None
            self.retryable = False
        elif error is not _UNSPECIFIED:
            self.error = error
            self.retryable = False
        elif retry is not _UNSPECIFIED:
            self.error = retry
            self.retryable = True
        else:
            raise TypeError(
                "Require one of 'result', 'error', or 'retry' parameters",
            )

    def failure(self, error):
        self.deferred.errback(error)

    def success(self, result):
        self.deferred.callback(result)
