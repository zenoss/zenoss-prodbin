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
from twisted.internet.task import LoopingCall
from twisted.spread import pb, banana, jelly
from zope.component import getUtility
from zope.event import notify

from Products.ZenHub.PBDaemon import RemoteException

from ..events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)
from ..interface import IHubServerConfig
from ..priority import (
    ModelingPaused,
    PrioritySelection,
    ServiceCallPriority,
    servicecall_priority_map,
)
from ..worklist import ZenHubWorklist
from ..utils import UNSPECIFIED as _UNSPECIFIED, getLogger

_InternalErrors = (
    pb.ProtocolError, banana.BananaError, jelly.InsecureJelly,
)
_RemoteErrors = (RemoteException, pb.RemoteError)


class WorkerPoolExecutor(object):
    """An executor that executes service calls using remote workers."""

    @classmethod
    def create(cls, name, config=None, pool=None):
        """Return a new executor instance.

        :param str name: The executor's name
        :param IHubServerConfig config: Configuration data
        :param WorkerPool pool: Where the zenhubworker references live
        :return: A new WorkerPoolExecutor instance.
        """
        if config is None:
            raise ValueError("Invalid value for 'config': None")
        if pool is None:
            raise ValueError("Invalid value for 'pool': None")
        modeling_paused = ModelingPaused(
            config.priorities["modeling"],
            config.modeling_pause_timeout,
        )
        selection = PrioritySelection(
            ServiceCallPriority, exclude=modeling_paused,
        )
        worklist = ZenHubWorklist(selection)
        return cls(name, worklist, pool)

    def __init__(self, name, worklist, pool):
        """Initialize a WorkerPoolExecutor instance."""
        self.__name = name
        self.__worklist = worklist
        self.__workers = pool
        self.__log = getLogger(self)
        self.__states = {
            "running": _Running(name, worklist, pool, self.__log),
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

    def stop(self):
        self.__state.stop()
        self.__state = self.__states["stopped"]

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        return self.__state.submit(call)

    def __repr__(self):
        return "<{0.__class__.__name__} '{1}'>".format(self, self.__name)


class _Stopped(object):
    """WorkerPoolExecutor in stopped state."""

    def stop(self):
        pass

    def submit(self, call):
        return defer.fail(pb.Error("ZenHub not ready."))


class _Running(object):
    """WorkerPoolExecutor in running state."""

    def __init__(self, name, worklist, pool, log):
        self.name = name
        self.worklist = worklist
        self.workers = pool
        self.log = log
        config = getUtility(IHubServerConfig)
        self.task_max_retries = config.task_max_retries
        self.loop = LoopingCall(self.dispatch)

    def start(self, reactor):
        self.reactor = reactor
        self.loopd = self.loop.start(0)

    def stop(self):
        self.loop.stop()

    def submit(self, call):
        task = ServiceCallTask(self.name, call)
        notify(task.received())
        self.log.info(
            "Received task service=%s method=%s id=%s",
            call.service, call.method, call.id.hex,
        )
        self.worklist.push(task.priority, task)
        return task.deferred

    @defer.inlineCallbacks
    def dispatch(self):
        """Schedule tasks for execution by workers."""
        self.log.debug(
            "There are %s workers currently available to work %s tasks "
            "worklist=%s",
            self.workers.available, len(self.worklist), self.name,
        )
        worker = None
        try:
            # Retrieve a task from the work queue
            task = yield self.worklist.pop()

            # Retrieve a worker to execute the task.
            worker = yield self.workers.hire()

            # Schedule the worker to execute the task
            self.reactor.callLater(0, self.execute, worker, task)
        except Exception:
            self.log.exception("Unexpected failure worklist=%s", self.name)
            # Layoff the worker (if a worker was hired)
            if worker:
                self.workers.layoff(worker)

    @defer.inlineCallbacks
    def execute(self, worker, task):
        """Execute the task using the worker.

        :param worker: The worker to execute the task
        :type worker: WorkerRef
        :param task: The task to be executed by the worker
        :type task: ServiceCallTask
        """
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
            self.log.exception("Unexpected failure worklist=%s", self.name)
        finally:
            # if the task is retryable, push the task
            # to the front of its queue.
            if task.retryable:
                self.worklist.pushfront(task.priority, task)
                self.log.debug(
                    "Task queued for retry service=%s method=%s id=%s",
                    task.call.service, task.call.method, task.call.id.hex,
                )
            # Make the worker available for work again
            self.workers.layoff(worker)

    def _handle_start(self, task, workerId):
        task.attempt += 1
        notify(task.started(workerId))
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
        notify(task.completed(retry=exception))
        self._log_incomplete(task)

    def _handle_success(self, task, result):
        # Send the result back to the submitter
        task.success(result)
        # Notify listeners of call completion (and success)
        notify(task.completed(result=result))
        self._log_completed(task)

    def _handle_failure(self, task, exception):
        # Send failure back to the submitter
        task.failure(exception)
        # Notify listeners of call completion (and failure)
        notify(task.completed(error=exception))
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
        "error", "retryable", "workerId", "event_data",
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
        self.event_data = dict(call)
        self.event_data.update({
            "queue": name,
            "priority": self.priority,
        })

    def received(self):
        """Return a ServiceCallReceived object."""
        self.received_tm = time.time()
        data = dict(self.event_data)
        data["timestamp"] = self.received_tm
        return ServiceCallReceived(**data)

    def started(self, workerId):
        """Return a ServiceCallStarted object."""
        self.started_tm = time.time()
        self.workerId = workerId
        self.event_data["worker"] = workerId
        data = dict(self.event_data)
        data.update({
            "timestamp": self.started_tm,
            "attempts": self.attempt,
        })
        return ServiceCallStarted(**data)

    def completed(
        self, result=_UNSPECIFIED, error=_UNSPECIFIED, retry=_UNSPECIFIED,
    ):
        """Return a ServiceCallCompleted object."""
        self.completed_tm = time.time()
        if result is not _UNSPECIFIED:
            key, value = ("result", result)
            self.error = None
            self.retryable = False
        elif error is not _UNSPECIFIED:
            key, value = ("error", error)
            self.error = error
            self.retryable = False
        elif retry is not _UNSPECIFIED:
            key, value = ("retry", retry)
            self.error = retry
            self.retryable = True
        else:
            raise TypeError(
                "Require one of 'result', 'error', or 'retry' parameters",
            )
        data = dict(self.event_data)
        data.update({
            "timestamp": self.completed_tm,
            "attempts": self.attempt,
            key: value,
        })
        return ServiceCallCompleted(**data)

    def failure(self, error):
        self.deferred.errback(error)

    def success(self, result):
        self.deferred.callback(result)
