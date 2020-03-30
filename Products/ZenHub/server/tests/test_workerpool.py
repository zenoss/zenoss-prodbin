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
from mock import Mock, patch
from twisted.internet import defer
from twisted.python.failure import Failure

from Products.ZenHub.server.service import ServiceCall

from ..workerpool import (
    RemoteServiceRegistry, WorkerPool, WorkerRef, WorkerAvailabilityQueue,
)

PATH = {'src': 'Products.ZenHub.server.workerpool'}


class WorkerPoolTest(TestCase):  # noqa: D101

    def setUp(self):
        self.queue = "default"
        self.pool = WorkerPool(self.queue)

    def test_name_property(self):
        self.assertEqual(self.queue, self.pool.name)

    def test_add_workers(self):
        worker1 = Mock(workerId=1, sessionId="1")
        worker2 = Mock(workerId=2, sessionId="2")

        self.pool.add(worker1)
        self.assertIn(worker1, self.pool)

        self.pool.add(worker2)
        self.assertIn(worker2, self.pool)

    def test_add_WorkerRef(self):
        worker = Mock(workerId=1, sessionId="1")
        services = Mock()
        workerref = WorkerRef(worker, services)

        with self.assertRaises(AssertionError):
            self.pool.add(workerref)

    def test_add_worker_twice(self):
        worker = Mock(workerId=1, sessionId="1")

        self.pool.add(worker)
        self.assertIn(worker, self.pool)

        self.pool.add(worker)
        self.assertIn(worker, self.pool)
        self.assertEqual(len(self.pool), 1)

    def test_add_duplicate_worker(self):
        worker = Mock(workerId=1, sessionId="1")
        worker_dup = Mock(workerId=1, sessionId="2")

        self.pool.add(worker)
        self.assertIn(worker, self.pool)

        self.pool.add(worker_dup)
        self.assertIn(worker_dup, self.pool)
        self.assertIn(worker, self.pool)

    def test_remove_worker(self):
        worker1 = Mock(workerId=1, sessionId="1")
        worker2 = Mock(workerId=2, sessionId="2")
        self.pool.add(worker1)
        self.pool.add(worker2)
        self.assertEqual(len(self.pool), 2)

        self.pool.remove(worker1)
        self.assertNotIn(worker1, self.pool)
        self.assertIn(worker2, self.pool)
        self.assertEqual(len(self.pool), 1)

        self.pool.remove(worker2)
        self.assertNotIn(worker1, self.pool)
        self.assertNotIn(worker2, self.pool)
        self.assertEqual(len(self.pool), 0)

    def test_remove_WorkerRef(self):
        worker = Mock(workerId=1, sessionId="1")
        services = Mock()
        workerref = WorkerRef(worker, services)

        with self.assertRaises(AssertionError):
            self.pool.add(workerref)

    def test_available(self):
        worker = Mock(workerId=1, sessionId="1")
        self.assertEqual(self.pool.available, 0)

        self.pool.add(worker)
        self.assertEqual(self.pool.available, 1)

        self.pool.remove(worker)
        self.assertEqual(self.pool.available, 0)

    def test_iter_protocol(self):
        w = next(iter(self.pool), None)
        self.assertIsNone(w)

        worker = Mock(workerId=1, sessionId="1")
        self.pool.add(worker)
        w = next(iter(self.pool), None)
        self.assertIsNotNone(w)
        self.assertIsInstance(w, WorkerRef)
        self.assertIs(w.ref, worker)

    def test_hire(self):
        worker = Mock(workerId=1, sessionId="1")
        worker.callRemote.return_value = defer.succeed("pong")

        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        def assign(x, v):
            x.value = v

        dfr = self.pool.hire()
        hired_worker = dfr.result

        self.assertIsInstance(hired_worker, WorkerRef)
        self.assertIs(hired_worker.ref, worker)
        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 1)

    def test_remove_after_hire(self):
        worker = Mock(workerId=1, sessionId="1")
        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        dfr = self.pool.hire()
        hired_worker = dfr.result
        self.pool.remove(hired_worker.ref)

        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 0)

    def test_hire_no_workers(self):
        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 0)

        dfr = self.pool.hire()
        # The deferred returned from the pool has not been called
        self.assertFalse(dfr.called)

    def test_wait_for_available_worker(self):
        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 0)

        dfr = self.pool.hire()
        # The deferred returned from the pool has not been called
        self.assertFalse(dfr.called)

        # a worker becomes available
        worker = Mock(workerId=1, sessionId="1")
        worker.callRemote.return_value = defer.succeed("pong")
        self.pool.add(worker)

        # the deferred is called, and the worker_reference_object is its result
        self.assertTrue(dfr.called)
        worker_ref = dfr.result
        self.assertIsInstance(worker_ref, WorkerRef)
        # the reference object contains the worker
        self.assertIs(worker_ref.ref, worker)

    def test_hire_no_available_workers(self):
        with patch.object(WorkerPool, "available", return_value=0)\
                as available:
            pool = WorkerPool(self.queue)
            worker = Mock(workerId=1, sessionId="1")
            pool.add(worker)

            available.__len__.return_value = 0
            self.assertEqual(len(pool), 1)

            dfr = self.pool.hire()
            self.assertFalse(dfr.called)

            available.pop.assert_not_called()

    def test_layoff(self):
        worker = Mock(workerId=1, sessionId="1")
        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        dfr = self.pool.hire()
        hired_worker = dfr.result

        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 1)

        self.pool.layoff(hired_worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

    def test_layoff_retired_worker(self):
        worker = Mock(workerId=1, sessionId="1")
        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        dfr = self.pool.hire()
        hired_worker = dfr.result

        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 1)

        worker2 = Mock(workerId=1, sessionId="2")
        self.pool.remove(worker)
        self.pool.add(worker2)
        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        self.pool.layoff(hired_worker)
        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

    def test_handleReportStatus(self):
        worker_1 = Mock(name='worker_1')
        worker_2 = Mock(name='worker_2')
        self.pool.add(worker_1)
        self.pool.add(worker_2)

        self.pool.handleReportStatus(event=None)

        worker_1.callRemote.assert_called_with("reportStatus")
        worker_2.callRemote.assert_called_with("reportStatus")


class RemoteServiceRegistryTest(TestCase):  # noqa: D101

    def setUp(self):
        self.worker = Mock(workerId=1, sessionId="1")
        self.registry = RemoteServiceRegistry(self.worker)

    def test_api(self):
        name = "service"
        monitor = "monitor"
        service = Mock()
        self.worker.callRemote.return_value = service

        svc = self.registry.get((name, monitor))
        self.assertIsNone(svc)
        self.assertNotIn((name, monitor), self.registry)

        dfr = self.registry.lookup(name, monitor)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertIs(dfr.result, service)

        svc = self.registry.get((name, monitor))
        self.assertIs(svc, service)
        self.assertIn((name, monitor), self.registry)

        # Note: 'callRemote' is called only once per (service, method).
        self.worker.callRemote.assert_called_once_with(
            "getService", name, monitor,
        )


class WorkerRefTest(TestCase):  # noqa: D101

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)
        self.logger = self.getLogger.return_value
        self.worker = Mock(workerId=1, sessionId="1")
        self.services = Mock(spec=RemoteServiceRegistry)
        self.ref = WorkerRef(self.worker, self.services)

    def test_properties(self):
        self.assertEqual(self.ref.ref, self.worker)
        self.assertEqual(self.ref.services, self.services)

    def test___getattr__(self):
        self.assertEqual(self.ref.workerId, self.worker.workerId)

    def test_run_no_arg_method(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[], kwargs={},
        )
        expected_result = service.callRemote.return_value

        dfr = self.ref.run(call)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertEqual(dfr.result, expected_result)
        self.services.lookup.assert_called_once_with(
            call.service, call.monitor,
        )
        service.callRemote.assert_called_once_with(call.method)

    def test_run_method_with_args(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=['arg'], kwargs={'arg': 1},
        )
        expected_result = service.callRemote.return_value

        dfr = self.ref.run(call)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertEqual(dfr.result, expected_result)
        self.services.lookup.assert_called_once_with(
            call.service, call.monitor,
        )
        service.callRemote.assert_called_once_with(
            call.method, call.args[0], arg=call.kwargs['arg'],
        )

    def test_run_lookup_failure(self):
        expected_error = ValueError("boom")
        self.services.lookup.side_effect = expected_error
        call = ServiceCall(
            monitor="localhost",
            service="the_service",
            method="method",
            args=[], kwargs={},
        )

        result = []
        dfr = self.ref.run(call)
        dfr.addErrback(lambda x: result.append(x))

        self.services.lookup.assert_called_once_with(
            call.service, call.monitor,
        )
        self.assertEqual(len(result), 1)
        failure = result[0]
        self.assertIsInstance(failure, Failure)
        actual_error = failure.value
        self.assertIsInstance(actual_error, ValueError)
        self.logger.error.assert_called_once_with(
            "Failed to retrieve remote service "
            "service=%s worker=%s error=(%s) %s",
            call.service, 1, "ValueError", expected_error,
        )

    def test_run_callremote_failure(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[], kwargs={},
        )
        expected_error = ValueError("boom")
        service.callRemote.side_effect = expected_error

        result = []
        dfr = self.ref.run(call)
        dfr.addErrback(lambda x: result.append(x))

        self.services.lookup.assert_called_once_with(
            call.service, call.monitor,
        )
        service.callRemote.assert_called_once_with(call.method)
        self.assertEqual(len(result), 1)
        failure = result[0]
        self.assertIsInstance(failure, Failure)
        actual_error = failure.value
        self.assertIsInstance(actual_error, ValueError)
        self.logger.error.assert_called_once_with(
            "Failed to execute remote method "
            "service=%s method=%s id=%s worker=%s error=(%s) %s",
            call.service, call.method, call.id.hex, 1,
            "ValueError", expected_error,
        )


class WorkerAvailabilityQueueTest(TestCase):
    """Test the WorkerAvailabilityQueue class."""

    def setUp(t):
        t.queue = WorkerAvailabilityQueue()

    def test_initial_state(t):
        q = WorkerAvailabilityQueue()
        t.assertEqual(0, len(q))
        t.assertTrue(hasattr(q, "pop"))

    def test_add(t):
        value = 10
        t.queue.add(value)
        t.assertEqual(1, len(t.queue))

    def test_add_and_pop(t):
        value = 10
        t.queue.add(value)
        dfr = t.queue.pop()
        t.assertEqual(dfr.result, value)

    def test_pop_empty(t):
        dfr = t.queue.pop()
        t.assertFalse(dfr.called)

    def test_deferred_pop(t):
        dfr = t.queue.pop()
        value = 10
        t.queue.add(value)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, value)

    def test_discard(t):
        value = 10
        t.queue.add(value)
        t.queue.discard(value)
        t.assertEqual(0, len(t.queue))

    def test_discard_empty(t):
        value = 10
        t.queue.discard(value)
        t.assertEqual(0, len(t.queue))
