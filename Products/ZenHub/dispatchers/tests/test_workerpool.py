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

from ..workers import ServiceCallJob
from ..workerpool import (
    WorkerPool, WorkerRef, ServiceRegistry,
)

PATH = {'src': 'Products.ZenHub.dispatchers.workerpool'}


class WorkerPoolTest(TestCase):

    def setUp(self):
        self.pool = WorkerPool()

    def test_add_workers(self):
        worker1 = Mock(workerId=1)
        worker2 = Mock(workerId=2)

        self.pool.add(worker1)
        self.assertIn(worker1, self.pool)

        self.pool.add(worker2)
        self.assertIn(worker2, self.pool)

    def test_add_WorkerRef(self):
        worker = Mock(workerId=1)
        services = Mock()
        workerref = WorkerRef(worker, services)

        with self.assertRaises(AssertionError):
            self.pool.add(workerref)

    def test_add_worker_twice(self):
        worker = Mock(workerId=1)

        self.pool.add(worker)
        self.assertIn(worker, self.pool)

        self.pool.add(worker)
        self.assertIn(worker, self.pool)
        self.assertEqual(len(self.pool), 1)

    def test_add_duplicate_worker(self):
        worker = Mock(workerId=1)
        worker_dup = Mock(workerId=1)

        self.pool.add(worker)
        self.assertIn(worker, self.pool)

        self.pool.add(worker_dup)
        self.assertIn(worker_dup, self.pool)
        self.assertNotIn(worker, self.pool)

    def test_remove_worker(self):
        worker1 = Mock(workerId=1)
        worker2 = Mock(workerId=2)
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
        worker = Mock(workerId=1)
        services = Mock()
        workerref = WorkerRef(worker, services)

        with self.assertRaises(AssertionError):
            self.pool.add(workerref)

    def test_available(self):
        worker = Mock(workerId=1)
        self.assertEqual(self.pool.available, 0)

        self.pool.add(worker)
        self.assertEqual(self.pool.available, 1)

        self.pool.remove(worker)
        self.assertEqual(self.pool.available, 0)

    def test_iter_protocol(self):
        w = next(iter(self.pool), None)
        self.assertIsNone(w)

        worker = Mock(workerId=1)
        self.pool.add(worker)
        w = next(iter(self.pool), None)
        self.assertIsNotNone(w)
        self.assertIsInstance(w, WorkerRef)
        self.assertIs(w.ref, worker)

    def test_borrow(self):
        worker = Mock(workerId=1)
        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        with self.pool.borrow() as borrowed_worker:
            self.assertEqual(self.pool.available, 0)
            self.assertEqual(len(self.pool), 1)
            self.assertIsInstance(borrowed_worker, WorkerRef)
            self.assertIs(borrowed_worker.ref, worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

    def test_remove_after_borrow(self):
        worker = Mock(workerId=1)
        self.pool.add(worker)

        self.assertEqual(self.pool.available, 1)
        self.assertEqual(len(self.pool), 1)

        with self.pool.borrow() as borrowed_worker:
            self.pool.remove(borrowed_worker.ref)

        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 0)

    def test_borrow_no_workers(self):
        self.assertEqual(self.pool.available, 0)
        self.assertEqual(len(self.pool), 0)

        with self.assertRaises(IndexError):
            with self.pool.borrow():
                pass

    def test_borrow_no_available_workers(self):
        with patch.object(WorkerPool, "available", return_value=0)\
                as available:
            pool = WorkerPool()
            worker = Mock(workerId=1)
            pool.add(worker)

            available.__len__.return_value = 0
            self.assertEqual(len(pool), 1)

            with self.assertRaises(IndexError):
                with self.pool.borrow():
                    pass

            available.pop.assert_not_called()
            available.append.assert_not_called()


class ServiceRegistryTest(TestCase):
    """
    """

    def setUp(self):
        self.worker = Mock(workerId=1)
        self.registry = ServiceRegistry(self.worker)

    def test_lookup(self):
        name = "service"
        monitor = "monitor"
        service = Mock()
        self.worker.callRemote.return_value = service

        svc = self.registry.get((name, monitor))
        self.assertIsNone(svc)
        self.assertFalse((name, monitor) in self.registry)

        dfr = self.registry.lookup(name, monitor)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertIs(dfr.result, service)

        svc = self.registry.get((name, monitor))
        self.assertIs(svc, service)
        self.assertTrue((name, monitor) in self.registry)


class WorkerRefTest(TestCase):
    """
    """

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.worker = Mock(workerId=1)
        self.services = Mock(spec=ServiceRegistry)
        self.ref = WorkerRef(self.worker, self.services)

    def test_properties(self):
        self.assertEqual(self.ref.ref, self.worker)
        self.assertEqual(self.ref.services, self.services)

    def test___getattr__(self):
        self.assertEqual(self.ref.workerId, self.worker.workerId)

    def test_run_no_arg_method(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        job = ServiceCallJob("service", "localhost", "method", [], {})
        expected_result = service.callRemote.return_value

        dfr = self.ref.run(job)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertEqual(dfr.result, expected_result)
        self.services.lookup.assert_called_once_with(job.service, job.monitor)
        service.callRemote.assert_called_once_with(job.method)

    def test_run_method_with_args(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        job = ServiceCallJob(
            "service", "localhost", "method", ['arg'], {'arg': 1}
        )
        expected_result = service.callRemote.return_value

        dfr = self.ref.run(job)

        self.assertIsInstance(dfr, defer.Deferred)
        self.assertTrue(dfr.called)
        self.assertEqual(dfr.result, expected_result)
        self.services.lookup.assert_called_once_with(job.service, job.monitor)
        service.callRemote.assert_called_once_with(
            job.method, job.args[0], arg=job.kwargs['arg']
        )

    def test_run_lookup_failure(self):
        original_error = ValueError("boom")
        self.services.lookup.side_effect = original_error
        job = ServiceCallJob("the_service", "localhost", "method", [], {})

        result = []
        dfr = self.ref.run(job)
        dfr.addErrback(lambda x: result.append(x))

        self.services.lookup.assert_called_once_with(job.service, job.monitor)
        self.assertEqual(len(result), 1)
        failure = result[0]
        self.assertIsInstance(failure, Failure)
        actual_error = failure.value
        self.assertIs(actual_error, original_error)

    def test_run_callremote_failure(self):
        service = Mock(spec=["callRemote"])
        self.services.lookup.return_value = service
        job = ServiceCallJob("service", "localhost", "method", [], {})
        original_error = ValueError("boom")
        service.callRemote.side_effect = original_error

        result = []
        dfr = self.ref.run(job)
        dfr.addErrback(lambda x: result.append(x))

        self.services.lookup.assert_called_once_with(job.service, job.monitor)
        service.callRemote.assert_called_once_with(job.method)
        self.assertEqual(len(result), 1)
        failure = result[0]
        self.assertIsInstance(failure, Failure)
        actual_error = failure.value
        self.assertIs(actual_error, original_error)
