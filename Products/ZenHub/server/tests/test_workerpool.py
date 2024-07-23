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
    RemoteServiceRegistry,
    WorkerPool,
    WorkerRef,
    WorkerAvailabilityQueue,
)

PATH = {"src": "Products.ZenHub.server.workerpool"}


class WorkerPoolTest(TestCase):  # noqa: D101
    def setUp(t):
        t.queue = "default"
        t.pool = WorkerPool(t.queue)

    def test_name_property(t):
        t.assertEqual(t.queue, t.pool.name)

    def test_add_workers(t):
        worker1 = Mock(spec=["name"])
        worker1.name = "default_1"
        worker2 = Mock(spec=["name"])
        worker2.name = "default_2"

        t.pool.add(worker1)
        t.assertIn(worker1, t.pool)

        t.pool.add(worker2)
        t.assertIn(worker2, t.pool)

        t.assertEqual(2, len(t.pool))

    def test_add_WorkerRef(t):
        worker = Mock(spec=["name"])
        worker.name = "default_1"
        services = Mock()
        workerref = WorkerRef(worker, services)

        with t.assertRaises(TypeError):
            t.pool.add(workerref)

    def test_add_worker_twice(t):
        worker = Mock(spec=["name"])
        worker.name = "default_1"

        t.pool.add(worker)
        t.assertIn(worker, t.pool)

        t.pool.add(worker)
        t.assertIn(worker, t.pool)

        t.assertEqual(len(t.pool), 1)

    def test_replace_worker(t):
        name = "default_1"
        worker = Mock(spec=["name"])
        worker.name = name
        worker_replacement = Mock(spec=["name"])
        worker_replacement.name = name

        t.pool.add(worker)
        t.assertEqual(len(t.pool), 1)
        t.assertIn(worker, t.pool)
        t.assertNotIn(worker_replacement, t.pool)

        t.pool.add(worker_replacement)
        t.assertEqual(len(t.pool), 1)
        t.assertIn(worker_replacement, t.pool)
        t.assertNotIn(worker, t.pool)

    def test_remove_worker(t):
        worker1 = Mock(spec=["name"])
        worker1.name = "default_1"
        worker2 = Mock(spec=["name"])
        worker2.name = "default_2"

        t.pool.add(worker1)
        t.pool.add(worker2)
        t.assertEqual(len(t.pool), 2)

        t.pool.remove(worker1)
        t.assertNotIn(worker1, t.pool)
        t.assertIn(worker2, t.pool)
        t.assertEqual(len(t.pool), 1)

        t.pool.remove(worker2)
        t.assertNotIn(worker1, t.pool)
        t.assertNotIn(worker2, t.pool)
        t.assertEqual(len(t.pool), 0)

    def test_remove_WorkerRef(t):
        worker = Mock(spec=["name"])
        worker.name = "default_1"
        services = Mock()
        workerref = WorkerRef(worker, services)

        with t.assertRaises(TypeError):
            t.pool.add(workerref)

    def test_available(t):
        worker = Mock(spec=["name"])
        worker.name = "default_1"
        t.assertEqual(t.pool.available, 0)

        t.pool.add(worker)
        t.assertEqual(t.pool.available, 1)

        t.pool.remove(worker)
        t.assertEqual(t.pool.available, 0)

    def test_iter_protocol(t):
        w = next(iter(t.pool), None)
        t.assertIsNone(w)

        worker = Mock(spec=["name"])
        worker.name = "default_1"
        t.pool.add(worker)
        w = next(iter(t.pool), None)
        t.assertIsNotNone(w)
        t.assertIsInstance(w, WorkerRef)
        t.assertIs(w.ref, worker)

    def test_hire(t):
        worker = Mock(spec=["name", "callRemote"])
        worker.name = "default_1"
        worker.callRemote.return_value = defer.succeed("pong")

        t.pool.add(worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        def assign(x, v):
            x.value = v

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertIsInstance(hired_worker, WorkerRef)
        t.assertIs(hired_worker.ref, worker)
        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 1)

    def test_remove_after_hire(t):
        worker = Mock(spec=["name", "callRemote"])
        worker.name = "default_1"
        t.pool.add(worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        dfr = t.pool.hire()
        hired_worker = dfr.result
        t.pool.remove(hired_worker.ref)

        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 0)

    def test_hire_no_workers(t):
        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 0)

        dfr = t.pool.hire()
        # The deferred returned from the pool has not been called
        t.assertFalse(dfr.called)

    def test_wait_for_available_worker(t):
        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 0)

        dfr = t.pool.hire()
        # The deferred returned from the pool has not been called
        t.assertFalse(dfr.called)

        # a worker becomes available
        worker = Mock(spec=["name", "callRemote"])
        worker.name = "default_1"
        worker.callRemote.return_value = defer.succeed("pong")
        t.pool.add(worker)

        # the deferred is called, and the worker_reference_object is its result
        t.assertTrue(dfr.called)
        worker_ref = dfr.result
        t.assertIsInstance(worker_ref, WorkerRef)
        # the reference object contains the worker
        t.assertIs(worker_ref.ref, worker)

    def test_hire_no_available_workers(t):
        with patch.object(
            WorkerPool, "available", return_value=0
        ) as available:
            pool = WorkerPool(t.queue)
            worker = Mock(spec=["name", "callRemote"])
            worker.name = "default_1"
            pool.add(worker)

            available.__len__.return_value = 0
            t.assertEqual(len(pool), 1)

            dfr = t.pool.hire()
            t.assertFalse(dfr.called)

            available.pop.assert_not_called()

    def test_layoff(t):
        worker = Mock(spec=["name", "callRemote"])
        worker.name = "default_1"
        t.pool.add(worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 1)

        t.pool.layoff(hired_worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

    def test_layoff_retired_worker(t):
        worker = Mock(spec=["name", "callRemote"])
        worker.name = "default_1"
        t.pool.add(worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 1)

        worker2 = Mock(spec=["name", "callRemote"])
        worker2.name = "default_1"
        t.pool.remove(worker)
        t.pool.add(worker2)
        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        t.pool.layoff(hired_worker)
        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

    def test_handleReportStatus(t):
        worker_1 = Mock(spec=["name", "callRemote"])
        worker_1.name = "default_1"
        worker_2 = Mock(spec=["name", "callRemote"])
        worker_2.name = "default_2"
        t.pool.add(worker_1)
        t.pool.add(worker_2)

        t.pool.handleReportStatus(event=None)

        worker_1.callRemote.assert_called_with("reportStatus")
        worker_2.callRemote.assert_called_with("reportStatus")


class RemoteServiceRegistryTest(TestCase):  # noqa: D101
    def setUp(t):
        t.worker = Mock(spec=["name", "callRemote"])
        t.worker.name = "default_1"
        t.registry = RemoteServiceRegistry(t.worker)

    def test_api(t):
        name = "service"
        monitor = "monitor"
        service = Mock()
        t.worker.callRemote.return_value = service

        svc = t.registry.get((name, monitor))
        t.assertIsNone(svc)
        t.assertNotIn((name, monitor), t.registry)

        dfr = t.registry.lookup(name, monitor)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertIs(dfr.result, service)

        svc = t.registry.get((name, monitor))
        t.assertIs(svc, service)
        t.assertIn((name, monitor), t.registry)

        # Note: 'callRemote' is called only once per (service, method).
        t.worker.callRemote.assert_called_once_with(
            "getService",
            name,
            monitor,
        )


class WorkerRefTest(TestCase):  # noqa: D101
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)
        t.logger = t.getLogger.return_value
        t.worker = Mock(spec=["name"])
        t.worker.name = "default_1"
        t.services = Mock(spec=RemoteServiceRegistry)
        t.ref = WorkerRef(t.worker, t.services)

    def test_properties(t):
        t.assertEqual(t.ref.ref, t.worker)
        t.assertEqual(t.ref.services, t.services)

    def test___getattr__(t):
        t.assertEqual(t.ref.name, t.worker.name)

    def test_run_no_arg_method(t):
        service = Mock(spec=["callRemote"])
        t.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[],
            kwargs={},
        )
        expected_result = service.callRemote.return_value

        dfr = t.ref.run(call)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, expected_result)
        t.services.lookup.assert_called_once_with(
            call.service,
            call.monitor,
        )
        service.callRemote.assert_called_once_with(call.method)

    def test_run_method_with_args(t):
        service = Mock(spec=["callRemote"])
        t.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=["arg"],
            kwargs={"arg": 1},
        )
        expected_result = service.callRemote.return_value

        dfr = t.ref.run(call)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, expected_result)
        t.services.lookup.assert_called_once_with(
            call.service,
            call.monitor,
        )
        service.callRemote.assert_called_once_with(
            call.method,
            call.args[0],
            arg=call.kwargs["arg"],
        )

    def test_run_lookup_failure(t):
        expected_error = ValueError("boom")
        t.services.lookup.side_effect = expected_error
        call = ServiceCall(
            monitor="localhost",
            service="the_service",
            method="method",
            args=[],
            kwargs={},
        )

        result = []
        dfr = t.ref.run(call)
        dfr.addErrback(lambda x: result.append(x))

        t.services.lookup.assert_called_once_with(
            call.service,
            call.monitor,
        )
        t.assertEqual(len(result), 1)
        failure = result[0]
        t.assertIsInstance(failure, Failure)
        actual_error = failure.value
        t.assertIsInstance(actual_error, ValueError)
        t.logger.error.assert_called_once_with(
            "Failed to retrieve remote service "
            "service=%s worker=%s error=(%s) %s",
            call.service,
            t.worker.name,
            "ValueError",
            expected_error,
        )

    def test_run_callremote_failure(t):
        service = Mock(spec=["callRemote"])
        t.services.lookup.return_value = service
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[],
            kwargs={},
        )
        expected_error = ValueError("boom")
        service.callRemote.side_effect = expected_error

        result = []
        dfr = t.ref.run(call)
        dfr.addErrback(lambda x: result.append(x))

        t.services.lookup.assert_called_once_with(
            call.service,
            call.monitor,
        )
        service.callRemote.assert_called_once_with(call.method)
        t.assertEqual(len(result), 1)
        failure = result[0]
        t.assertIsInstance(failure, Failure)
        actual_error = failure.value
        t.assertIsInstance(actual_error, ValueError)
        t.logger.error.assert_called_once_with(
            "Failed to execute remote method "
            "service=%s method=%s id=%s worker=%s error=(%s) %s",
            call.service,
            call.method,
            call.id.hex,
            t.worker.name,
            "ValueError",
            expected_error,
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
