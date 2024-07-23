##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.internet import defer
from twisted.spread import pb
from zope.event import notify

from Products.ZenHub.errors import RemoteException

from .event import started, completed


class TaskDispatcher(object):
    """
    Execute (dispatch) a task to worker and handle the result.
    """

    def __init__(self, worker, task, log):
        self.worker = worker
        self.task = task
        self.log = log

    @defer.inlineCallbacks
    def __call__(self):
        """Execute the task using the worker.

        :param worker: The worker to execute the task
        :type worker: WorkerRef
        :param task: The task to be executed by the worker
        :type task: ServiceCallTask
        """
        try:
            # Prepare to execute the task.
            self.task.mark_started(self.worker.name)
            notify(started(self.task))

            # Execute the task
            result = yield self.worker.run(self.task.call)

            # Mark the task execution as successful
            self.task.mark_success(result)
            status = "result"
        except (RemoteException, pb.RemoteError) as ex:
            # These are unretryable errors that originate from the service
            # and are propagated directly back to the submitter.
            self.task.mark_failure(ex)
            status, result = "error", ex
        except pb.PBConnectionLost as ex:
            # Lost connection to the worker; not a failure.
            self.log.warn(
                "worker no longer accepting tasks  worker=%s",
                self.worker.name,
            )
            if self.task.retryable:
                self.task.mark_retry(ex)
                status, result = "retry", ex
            else:
                self.log.warn(
                    "retries exhausted  "
                    "collector=%s service=%s method=%s id=%s",
                    self.task.call.monitor,
                    self.task.call.service,
                    self.task.call.method,
                    self.task.call.id.hex,
                )
                self.task.mark_failure(ex)
                status, result = "error", ex
        except Exception as ex:
            # 'catch-all' error handler and tasks are not retryable.
            self.task.mark_failure(self._to_failure(ex))
            status, result = "error", ex
            self.log.exception(
                "unexpected failure  "
                "worklist=%s collector=%s service=%s method=%s id=%s",
                self.name,
                self.task.call.monitor,
                self.task.call.service,
                self.task.call.method,
                self.task.call.id.hex,
            )
        finally:
            notify(completed(self.task, status, result))

    def _to_failure(self, exception):
        return pb.Error(
            ("Internal ZenHub error: ({0.__class__.__name__}) {0}")
            .format(exception)
            .strip()
        )
