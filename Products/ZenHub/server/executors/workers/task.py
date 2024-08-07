##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import time

import attr

from attr.validators import instance_of
from twisted.internet import defer

from ...priority import servicecall_priority_map
from ...service import ServiceCall

log = logging.getLogger("zen.zenhub.server.task")


@attr.s(slots=True)
class ServiceCallTask(object):
    """Wraps a ServiceCall to track for use with WorkerPoolExecutor."""

    worklist = attr.ib()
    call = attr.ib(validator=instance_of(ServiceCall))
    max_retries = attr.ib()

    deferred = attr.ib(factory=defer.Deferred)

    attempt = attr.ib(default=0)
    received_tm = attr.ib(default=None)
    started_tm = attr.ib(default=None)
    completed_tm = attr.ib(default=None)
    worker_name = attr.ib(default=None)

    # These attributes are initialized in __attrs_post_init__.
    desc = attr.ib(init=False)
    priority = attr.ib(init=False)
    event_data = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.desc = "%s:%s.%s" % (
            self.call.monitor,
            self.call.service,
            self.call.method,
        )
        self.priority = servicecall_priority_map.get(
            (self.call.service, self.call.method),
        )
        self.event_data = attr.asdict(self.call)
        self.event_data.update(
            {
                "queue": self.worklist,
                "priority": self.priority,
            }
        )

    @property
    def retryable(self):
        """
        Return True if the task can be re-executed.
        """
        if self.deferred.called:
            return False
        return self.attempt <= self.max_retries

    def mark_received(self):
        """
        Update the task's state to indicate task acceptance.
        """
        self.received_tm = time.time()
        log.info(
            "received task  collector=%s service=%s method=%s id=%s",
            self.call.monitor,
            self.call.service,
            self.call.method,
            self.call.id.hex,
        )

    def mark_started(self, worker_name):
        """
        Update the task's state to indicate the task's execution.
        """
        self.attempt += 1
        self.started_tm = time.time()
        self.worker_name = worker_name
        self.event_data["worker"] = worker_name  # needed for completed event
        if self.attempt == 1:
            _log_initial_attempt(self)
        else:
            _log_subsequent_attempts(self)

    def mark_success(self, result):
        """
        Update the task's state to indicate the task's successful completion.
        """
        self.completed_tm = time.time()
        self.deferred.callback(result)
        _log_completed("success", self)

    def mark_failure(self, error):
        """
        Update the task's state to indicate the task's failed completion.
        """
        self.completed_tm = time.time()
        self.deferred.errback(error)
        _log_completed("failed", self)

    def mark_retry(self, error):
        """
        Update the task's state to indicate the task's incomplete execution.
        """
        self.completed_tm = time.time()
        elapsed = self.task.completed_tm - self.task.started_tm
        log.info(
            "failed to complete task  collector=%s service=%s method=%s "
            "id=%s worker=%s duration=%0.2f error=%s",
            self.task.call.monitor,
            self.task.call.service,
            self.task.call.method,
            self.task.call.id.hex,
            self.task.worker_name,
            elapsed,
            error,
        )


def _log_initial_attempt(task):
    waited = task.started_tm - task.received_tm
    log.info(
        "begin task  "
        "collector=%s service=%s method=%s id=%s worker=%s waited=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        waited,
    )

def _log_subsequent_attempts(task):
    waited = task.started_tm - task.completed_tm
    log.info(
        "retry task  collector=%s service=%s method=%s id=%s "
        "worker=%s attempt=%s waited=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        task.attempt,
        waited,
    )

def _log_completed(status, task):
    elapsed = task.completed_tm - task.started_tm
    lifetime = task.completed_tm - task.received_tm
    log.info(
        "completed task  collector=%s service=%s method=%s id=%s "
        "worker=%s status=%s duration=%0.2f lifetime=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        status,
        elapsed,
        lifetime,
    )
