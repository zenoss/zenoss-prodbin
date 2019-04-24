##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import (
    NonCallableMagicMock, Mock, patch,
)
from twisted.internet import defer, reactor
from twisted.python.failure import Failure
from twisted.spread import pb

from Products.ZenHub.server.metrics import StatsMonitor
from Products.ZenHub.server.service import ServiceCall
from Products.ZenHub.server.worklist import ZenHubWorklist
from Products.ZenHub.server.workerpool import WorkerPool
from Products.ZenHub.server.utils import subTest

from ..workers import (
    WorkerPoolExecutor,
    ServiceCallTask,
    _Running,
    RemoteException, banana, jelly,
)

PATH = {'src': 'Products.ZenHub.server.executors.workers'}


class WorkerPoolExecutorTest(TestCase):  # noqa: D101

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self._Running_patcher = patch(
            "{src}._Running".format(**PATH), autospec=True,
        )
        self._Running = self._Running_patcher.start()
        self.addCleanup(self._Running_patcher.stop)

        self.reactor = Mock(spec=reactor)
        self.worklist = NonCallableMagicMock(spec=ZenHubWorklist)
        self.workers = NonCallableMagicMock(spec=WorkerPool)
        self.monitor = NonCallableMagicMock(spec=StatsMonitor)

        self.name = "default"
        self.executor = WorkerPoolExecutor(
            self.name, self.worklist, self.workers, self.monitor,
        )
        self.logger = self.getLogger(self.executor)

    def test_initial_state(self):
        self.assertEqual(self.name, self.executor.name)
        self.assertEqual(self.workers, self.executor.pool)

        call = Mock(spec=ServiceCall)
        handler = Mock()
        dfr = self.executor.submit(call)
        dfr.addErrback(handler)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, pb.Error)
        self.assertEqual("ZenHub not ready.", str(f.value))
        self._Running.assert_called_once_with(
            self.name, self.worklist, self.workers, self.monitor, self.logger,
        )

    def test_start(self):
        call = Mock(spec=ServiceCall)
        running_state = self._Running.return_value

        self.executor.start(self.reactor)
        dfr = self.executor.submit(call)

        self.assertEqual(dfr, running_state.submit.return_value)


class BaseRunning(object):
    """Base for the Running*Test classes.

    The setUp() method contains common setup code all tests use.
    """

    def setUp(self):
        super(BaseRunning, self).setUp()
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.getUtility_patcher = patch(
            "{src}.getUtility".format(**PATH), autospec=True,
        )
        self.getUtility = self.getUtility_patcher.start()
        self.addCleanup(self.getUtility_patcher.stop)

        self.max_retries = self.getUtility.return_value.task_max_retries
        self.logger = self.getLogger.return_value
        self.workers = NonCallableMagicMock(spec=WorkerPool)
        self.worklist = NonCallableMagicMock(spec=ZenHubWorklist)
        self.monitor = NonCallableMagicMock(spec=StatsMonitor)
        self.name = "default"
        self.running = _Running(
            self.name, self.worklist, self.workers, self.monitor, self.logger,
        )
        self.reactor = Mock(spec=reactor)


class RunningTest(BaseRunning, TestCase):
    """Test the _Running class."""

    def test_initial_state(self):
        self.assertIs(self.running.log, self.logger)
        self.assertIs(self.running.name, self.name)
        self.assertIs(self.running.worklist, self.worklist)
        self.assertIs(self.running.workers, self.workers)
        self.assertIs(self.running.task_max_retries, self.max_retries)

    def test_start(self):
        self.running.start(self.reactor)
        self.assertIs(self.running.reactor, self.reactor)

    @patch("{src}.ServiceCallTask".format(**PATH), autospec=True)
    def test_submit(self, _ServiceCallTask):
        self.running.start(self.reactor)

        call = Mock(spec=ServiceCall)
        task = _ServiceCallTask.return_value
        expected_priority = task.priority
        expected_dfr = task.deferred

        dfr = self.running.submit(call)

        self.assertIs(expected_dfr, dfr)
        _ServiceCallTask.assert_called_once_with(self.name, call)
        self.worklist.push.assert_called_once_with(expected_priority, task)
        self.reactor.callLater.assert_called_once_with(
            0, self.running.execute,
        )

    def test_execute_no_tasks(self):
        self.running.start(self.reactor)

        self.worklist.__len__.return_value = 0
        self.workers.available = True

        dfr = self.running.execute()

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertIsNone(dfr.result)
        self.workers.hire.assert_not_called()
        self.worklist.pop.assert_not_called()
        self.reactor.callLater.assert_not_called()

    def test_execute_no_workers(self):
        self.running.start(self.reactor)

        self.worklist.__len__.return_value = 1
        self.workers.hire.return_value = None

        dfr = self.running.execute()

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertIsNone(dfr.result)
        self.workers.hire.assert_called_once_with()
        self.worklist.pop.assert_not_called()
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )

    def test_execute_worker_hire_failure(self):
        self.running.start(self.reactor)

        self.worklist.__len__.return_value = 1
        self.workers.hire.side_effect = Exception("boom")

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        self.assertIsInstance(dfr, defer.Deferred)
        self.workers.hire.assert_called_once_with()
        self.logger.exception.assert_called_once_with("Unexpected failure")
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )

        handler.assert_not_called()
        self.logger.debug.assert_not_called()
        self.logger.info.assert_not_called()
        self.logger.warn.assert_not_called()
        self.logger.error.assert_not_called()
        self.workers.layoff.assert_not_called()
        self.worklist.pop.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test_execute_pop_failure(self):
        self.running.start(self.reactor)

        self.worklist.__len__.return_value = 1
        self.worklist.pop.side_effect = Exception("boom")
        worker = Mock(spec=["workerId", "run"])
        self.workers.hire.return_value = worker

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        self.assertIsInstance(dfr, defer.Deferred)
        self.workers.hire.assert_called_once_with()
        self.worklist.pop.assert_called_once_with()
        self.logger.exception.assert_called_once_with("Unexpected failure")
        self.workers.layoff.assert_called_once_with(worker)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )

        handler.assert_not_called()
        worker.run.assert_not_called()
        self.logger.info.assert_not_called()
        self.logger.warn.assert_not_called()
        self.logger.error.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test_execute_pop_returns_none(self):
        self.running.start(self.reactor)

        self.worklist.__len__.return_value = 1
        self.worklist.pop.return_value = None
        worker = Mock(spec=["workerId", "run"])
        self.workers.hire.return_value = worker

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        self.assertIsInstance(dfr, defer.Deferred)
        self.workers.hire.assert_called_once_with()
        self.worklist.pop.assert_called_once_with()
        self.workers.layoff.assert_called_once_with(worker)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )
        handler.assert_not_called()
        worker.run.assert_not_called()
        self.logger.info.assert_not_called()
        self.logger.warn.assert_not_called()
        self.logger.error.assert_not_called()
        self.logger.exception.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test__log_initial_start(self):
        call = Mock(spec=ServiceCall)
        task = Mock(spec=ServiceCallTask)
        task.call = call
        task.received_tm = 10
        task.started_tm = 20
        task.workerId = "default_0"

        self.running._log_initial_start(task)

        self.logger.info.assert_called_once_with(
            "Begin task service=%s method=%s id=%s worker=%s waited=%0.2f",
            call.service, call.method, call.id.hex, "default_0", 10,
        )

    def test__log_subsequent_starts(self):
        call = Mock(spec=ServiceCall)
        task = Mock(spec=ServiceCallTask)
        task.call = call
        task.attempt = 1
        task.completed_tm = 10
        task.started_tm = 30
        task.workerId = "default_0"

        self.running._log_subsequent_starts(task)

        self.logger.info.assert_called_once_with(
            "Retry task service=%s method=%s id=%s "
            "worker=%s attempt=%s waited=%0.2f",
            call.service, call.method, call.id.hex,
            "default_0", task.attempt, 20,
        )

    def test__log_complete(self):
        call = Mock(spec=ServiceCall)
        task = Mock(spec=ServiceCallTask)
        task.call = call
        task.error = None
        task.received_tm = 10
        task.started_tm = 20
        task.completed_tm = 30
        task.workerId = "default_0"

        self.running._log_completed(task)

        self.logger.info.assert_called_once_with(
            "Completed task service=%s method=%s id=%s "
            "worker=%s status=%s duration=%0.2f lifetime=%0.2f",
            call.service, call.method, call.id.hex,
            task.workerId, "success", 10, 20,
        )


class RunningHandleMethodsTest(BaseRunning, TestCase):
    """Test the _handle_* methods on the _Running class."""

    def setUp(self):
        super(RunningHandleMethodsTest, self).setUp()
        methods_to_patch = (
            "_log_initial_start", "_log_subsequent_starts",
            "_log_incomplete", "_log_completed",
        )
        self.patchers = []
        self.patches = {}
        for method in methods_to_patch:
            patcher = patch.object(self.running, method)
            self.patches[method] = patcher.start()
            self.addCleanup(patcher.stop)
            self.patchers.append(patcher)
        self.running.start(self.reactor)

    def test__handle_start_first_attempt(self):
        task = Mock(spec=["attempt", "started", "call"])
        task.attempt = 0
        workerId = 1

        self.running._handle_start(task, workerId)

        self.assertEqual(1, task.attempt)
        task.started.assert_called_once_with(workerId)

        self.patches["_log_initial_start"].assert_called_once_with(task)
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_not_called()

    def test__handle_start_later_attempts(self):
        task = Mock(spec=["attempt", "started", "call"])
        task.attempt = 1
        workerId = 1

        self.running._handle_start(task, workerId)

        self.assertEqual(2, task.attempt)
        task.started.assert_called_once_with(workerId)

        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_called_once_with(task)
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_not_called()

    def test__handle_error_with_retries(self):
        _handle_failure_patch = patch.object(self.running, "_handle_failure")
        _handle_failure = _handle_failure_patch.start()
        self.addCleanup(_handle_failure_patch.stop)

        _handle_retry_patch = patch.object(self.running, "_handle_retry")
        _handle_retry = _handle_retry_patch.start()
        self.addCleanup(_handle_retry_patch.stop)

        task = Mock(spec=["attempt"])
        task.attempt = 1
        self.running.task_max_retries = 3
        error = Exception()

        self.running._handle_error(task, error)

        _handle_failure.assert_not_called()
        _handle_retry.assert_called_once_with(task, error)
        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_not_called()

    @patch("{src}.pb.Error".format(**PATH), autospec=True)
    def test__handle_error_no_retries(self, _Error):
        _handle_failure_patch = patch.object(self.running, "_handle_failure")
        _handle_failure = _handle_failure_patch.start()
        self.addCleanup(_handle_failure_patch.stop)

        _handle_retry_patch = patch.object(self.running, "_handle_retry")
        _handle_retry = _handle_retry_patch.start()
        self.addCleanup(_handle_retry_patch.stop)

        task = Mock(spec=["attempt", "call"])
        task.attempt = 3
        self.running.task_max_retries = 3
        error = Exception()

        self.running._handle_error(task, error)

        _handle_failure.assert_called_once_with(task, _Error.return_value)
        _handle_retry.assert_not_called()
        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_not_called()

    @patch("{src}.notify".format(**PATH), autospec=True)
    def test__handle_retry(self, _notify):
        task = Mock(spec=["success", "completed", "workerId", "call"])
        exception = Mock()

        self.running._handle_retry(task, exception)

        task.completed.assert_called_once_with(retry=exception)
        _notify.assert_called_once_with(task.completed.return_value)

        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_completed"].assert_not_called()
        self.patches["_log_incomplete"].assert_called_once_with(task)

    @patch("{src}.notify".format(**PATH), autospec=True)
    def test__handle_success(self, _notify):
        task = Mock(spec=["success", "completed", "workerId", "call"])
        result = Mock()

        self.running._handle_success(task, result)

        self.reactor.callLater.assert_called_once_with(
            0, task.success, result,
        )
        task.completed.assert_called_once_with(result=result)
        _notify.assert_called_once_with(task.completed.return_value)

        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_called_once_with(task)

    @patch("{src}.notify".format(**PATH), autospec=True)
    def test__handle_failure(self, _notify):
        task = Mock(spec=["failure", "completed", "workerId", "call"])
        error = Mock()

        self.running._handle_failure(task, error)

        self.reactor.callLater.assert_called_once_with(
            0, task.failure, error,
        )
        task.completed.assert_called_once_with(error=error)
        _notify.assert_called_once_with(task.completed.return_value)

        self.patches["_log_initial_start"].assert_not_called()
        self.patches["_log_subsequent_starts"].assert_not_called()
        self.patches["_log_incomplete"].assert_not_called()
        self.patches["_log_completed"].assert_called_once_with(task)


class RunningExecuteTest(BaseRunning, TestCase):
    """More complex testing of the execute method on the _Running class."""

    def setUp(self):
        super(RunningExecuteTest, self).setUp()
        methods_to_patch = (
            "_handle_start", "_handle_retry", "_handle_error",
            "_handle_success", "_handle_failure",
        )
        self.patchers = []
        self.patches = {}
        for method in methods_to_patch:
            patcher = patch.object(self.running, method)
            self.patches[method] = patcher.start()
            self.addCleanup(patcher.stop)
            self.patchers.append(patcher)
        self.running.start(self.reactor)

    def test_nominal_execute(self):
        task = Mock(spec=["call", "retryable"])
        task.retryable = False
        self.worklist.__len__.return_value = 1
        self.worklist.pop.return_value = task
        worker = Mock(spec=["workerId", "run"])
        self.workers.hire.return_value = worker
        expected_result = worker.run.return_value

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        handler.assert_not_called()
        self.assertIsInstance(dfr, defer.Deferred)
        self.worklist.pop.assert_called_once_with()
        worker.run.assert_called_once_with(task.call)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )
        self.patches["_handle_start"].assert_called_once_with(
            task, worker.workerId,
        )
        self.patches["_handle_success"].assert_called_once_with(
            task, expected_result,
        )

        self.logger.exception.assert_not_called()
        self.logger.error.assert_not_called()
        self.logger.warn.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()
        self.patches["_handle_failure"].assert_not_called()
        self.patches["_handle_error"].assert_not_called()
        self.patches["_handle_retry"].assert_not_called()

    def test_remote_errors(self):
        worker = Mock(spec=["workerId", "run"])
        exc = ValueError("boom")
        errors = (
            RemoteException("RemoteBoom", None),
            pb.RemoteError(ValueError, exc, None),
        )

        for error in errors:
            with subTest(error=error):
                worker.run.side_effect = error
                task = Mock(spec=["call", "retryable", "priority"])
                task.retryable = True
                self.worklist.__len__.return_value = 1
                self.worklist.pop.return_value = task
                self.workers.hire.return_value = worker

                handler = Mock()
                dfr = self.running.execute()
                dfr.addErrback(handler)

                handler.assert_not_called()
                self.assertIsInstance(dfr, defer.Deferred)
                self.worklist.pop.assert_called_once_with()
                worker.run.assert_called_once_with(task.call)
                self.patches["_handle_start"].assert_called_once_with(
                    task, worker.workerId,
                )
                self.patches["_handle_failure"].assert_called_once_with(
                    task, error,
                )
                self.workers.layoff.assert_called_once_with(worker)
                self.reactor.callLater.assert_called_once_with(
                    0.1, self.running.execute,
                )

                self.logger.exception.assert_not_called()
                self.logger.error.assert_not_called()
                self.logger.warn.assert_not_called()
                self.logger.info.assert_not_called()
                self.worklist.push.assert_not_called()
                self.patches["_handle_success"].assert_not_called()
                self.patches["_handle_error"].assert_not_called()
                self.patches["_handle_retry"].assert_not_called()

            worker.reset_mock()
            for patched in self.patches.values():
                patched.reset_mock()
            self.logger.reset_mock()
            self.reactor.reset_mock()
            self.worklist.reset_mock()
            self.workers.reset_mock()

    @patch("{src}.pb.Error".format(**PATH), autospec=True)
    def test_internal_errors(self, _Error):
        worker = Mock(spec=["workerId", "run"])
        errors = (
            pb.ProtocolError(), banana.BananaError(), jelly.InsecureJelly(),
        )

        for error in errors:
            with subTest(error=error):
                worker.run.side_effect = error

                task = Mock(spec=["call", "retryable", "priority"])
                task.retryable = True
                self.worklist.__len__.return_value = 1
                self.worklist.pop.return_value = task
                self.workers.hire.return_value = worker

                handler = Mock()
                dfr = self.running.execute()
                dfr.addErrback(handler)

                handler.assert_not_called()
                self.assertIsInstance(dfr, defer.Deferred)
                self.worklist.pop.assert_called_once_with()
                worker.run.assert_called_once_with(task.call)
                self.patches["_handle_start"].assert_called_once_with(
                    task, worker.workerId,
                )
                self.logger.error.assert_called_once_with(
                    "(%s) %s service=%s method=%s id=%s worker=%s",
                    type(error), error,
                    task.call.service, task.call.method,
                    task.call.id, worker.workerId,
                )
                self.patches["_handle_failure"].assert_called_once_with(
                    task, _Error.return_value,
                )
                self.workers.layoff.assert_called_once_with(worker)
                self.reactor.callLater.assert_called_once_with(
                    0.1, self.running.execute,
                )

                self.logger.exception.assert_not_called()
                self.logger.warn.assert_not_called()
                self.logger.info.assert_not_called()
                self.worklist.push.assert_not_called()
                self.patches["_handle_success"].assert_not_called()
                self.patches["_handle_error"].assert_not_called()
                self.patches["_handle_retry"].assert_not_called()

            worker.reset_mock()
            for patched in self.patches.values():
                patched.reset_mock()
            self.logger.reset_mock()
            self.reactor.reset_mock()
            self.worklist.reset_mock()
            self.workers.reset_mock()

    def test_execute_PBConnectionLost(self):
        error = pb.PBConnectionLost()
        worker = Mock(spec=["workerId", "run"])
        worker.run.side_effect = error

        task = Mock(spec=["call", "retryable", "priority"])
        task.retryable = True
        self.worklist.__len__.return_value = 1
        self.worklist.pop.return_value = task
        self.workers.hire.return_value = worker

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        handler.assert_not_called()
        self.assertIsInstance(dfr, defer.Deferred)
        self.worklist.pop.assert_called_once_with()
        worker.run.assert_called_once_with(task.call)
        self.patches["_handle_start"].assert_called_once_with(
            task, worker.workerId,
        )
        self.patches["_handle_retry"].assert_called_once_with(task, error)
        self.worklist.pushfront.assert_called_once_with(
            task.priority, task,
        )
        self.workers.layoff.assert_called_once_with(worker)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )

        self.logger.error.assert_not_called()
        self.worklist.push.assert_not_called()
        self.patches["_handle_success"].assert_not_called()
        self.patches["_handle_failure"].assert_not_called()
        self.patches["_handle_error"].assert_not_called()

    def test_execute_unexpected_error(self):
        error = Exception()
        worker = Mock(spec=["workerId", "run"])
        worker.run.side_effect = error

        task = Mock(spec=["call", "retryable", "attempt", "priority"])
        task.retryable = True
        self.worklist.__len__.return_value = 1
        self.worklist.pop.return_value = task
        self.workers.hire.return_value = worker

        handler = Mock()
        dfr = self.running.execute()
        dfr.addErrback(handler)

        handler.assert_not_called()
        self.assertIsInstance(dfr, defer.Deferred)
        self.worklist.pop.assert_called_once_with()
        worker.run.assert_called_once_with(task.call)
        self.patches["_handle_start"].assert_called_once_with(
            task, worker.workerId,
        )
        self.patches["_handle_error"].assert_called_once_with(
            task, error,
        )
        self.worklist.pushfront.assert_called_once_with(
            task.priority, task,
        )
        self.workers.layoff.assert_called_once_with(worker)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.running.execute,
        )
        self.logger.exception.assert_called_once_with("Unexpected failure")

        self.logger.error.assert_not_called()
        self.logger.warn.assert_not_called()
        self.logger.info.assert_not_called()
        self.worklist.push.assert_not_called()
        self.patches["_handle_success"].assert_not_called()
        self.patches["_handle_failure"].assert_not_called()
        self.patches["_handle_retry"].assert_not_called()


class ServiceCallTaskTest(TestCase):
    """Test the ServiceCallTask class."""

    def setUp(self):
        self.queue = "queue"
        self.monitor = "localhost"
        self.service = "service"
        self.method = "method"
        self.call = ServiceCall(
            monitor=self.monitor,
            service=self.service,
            method=self.method,
            args=[],
            kwargs={},
        )
        self.task = ServiceCallTask(self.queue, self.call)

    def test_expected_attributes(self):
        expected_attrs = tuple(sorted((
            "call", "deferred", "desc", "attempt", "priority",
            "received_tm", "started_tm", "completed_tm",
            "error", "retryable", "workerId",
            "received", "started", "completed",
            "failure", "success",
        )))
        actual_attrs = tuple(sorted(
            n for n in dir(self.task) if not n.startswith("_")
        ))
        self.assertTupleEqual(expected_attrs, actual_attrs)

    def test_failure_attribute(self):
        self.assertTrue(callable(self.task.failure))

    def test_success_attribute(self):
        self.assertTrue(callable(self.task.success))

    def test_call_attribute(self):
        self.assertIs(self.call, self.task.call)

    def test_deferred_attribute(self):
        self.assertIsInstance(self.task.deferred, defer.Deferred)

    def test_desc_attribute(self):
        expected_desc = "%s:%s.%s" % (self.monitor, self.service, self.method)
        self.assertEqual(expected_desc, self.task.desc)

    def test_initial_attempt_value(self):
        self.assertEqual(0, self.task.attempt)

    def test_initial_error_value(self):
        self.assertIsNone(self.task.error)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_received(self, _time):
        expected_tm = _time.time.return_value
        self.task.received()
        self.assertEqual(expected_tm, self.task.received_tm)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_started(self, _time):
        self.task.attempt = 1
        expected_tm = _time.time.return_value
        workerId = "default_0"
        self.task.started(workerId)
        self.assertEqual(expected_tm, self.task.started_tm)
        self.assertEqual(1, self.task.attempt)
        self.assertEqual(workerId, self.task.workerId)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_completed_with_retry(self, _time):
        self.task.error = Mock()
        self.task.attempt = 2
        expected_tm = _time.time.return_value
        error = Mock()

        self.task.completed(retry=error)

        self.assertTrue(self.task.retryable)
        self.assertEqual(expected_tm, self.task.completed_tm)
        self.assertEqual(2, self.task.attempt)
        self.assertEqual(error, self.task.error)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_completed_with_success(self, _time):
        self.task.attempt = 1
        expected_tm = _time.time.return_value
        result = Mock()

        self.task.completed(result=result)

        self.assertFalse(self.task.retryable)
        self.assertEqual(expected_tm, self.task.completed_tm)
        self.assertEqual(1, self.task.attempt)
        self.assertIsNone(self.task.error)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_completed_with_error(self, _time):
        self.task.attempt = 1
        expected_tm = _time.time.return_value
        error = Mock()

        self.task.completed(error=error)

        self.assertFalse(self.task.retryable)
        self.assertEqual(expected_tm, self.task.completed_tm)
        self.assertEqual(1, self.task.attempt)
        self.assertIs(self.task.error, error)
