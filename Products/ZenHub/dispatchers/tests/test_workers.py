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
    NonCallableMagicMock, MagicMock, Mock,
    call, patch, sentinel, ANY
)
from twisted.internet import defer, reactor
from twisted.spread import pb

from Products.ZenHub.worklist import ZenHubWorklist

from ..workers import (
    WorkerPoolDispatcher,
    ServiceCallJob, AsyncServiceCallJob,
    StatsMonitor, WorkerStats, JobStats,
    RemoteException
)
from ..workerpool import WorkerPool, WorkerRef, ServiceCallError

PATH = {'src': 'Products.ZenHub.dispatchers.workers'}


class WorkerPoolDispatcherTest(TestCase):

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.reactor = Mock(spec=reactor)
        self.worklist = NonCallableMagicMock(spec=ZenHubWorklist)
        self.workers = NonCallableMagicMock(spec=WorkerPool)
        self.stats = NonCallableMagicMock(spec=StatsMonitor)

        cm = MagicMock(spec=("__enter__", "__exit__"))
        cm.__enter__.return_value = self.stats
        self.stats.monitor.return_value = cm

        self.dispatcher = WorkerPoolDispatcher(
            self.reactor, self.worklist, self.workers, self.stats
        )
        self.logger = self.getLogger("zenhub", self.dispatcher)

    def test_routes(self):
        self.assertEqual((), self.dispatcher.routes)

    @patch("{src}.AsyncServiceCallJob".format(**PATH))
    def test_submit(self, asyncjob):
        job = Mock(spec=ServiceCallJob)
        ajob = asyncjob.return_value
        expected_dfr = ajob.deferred
        dfr = self.dispatcher.submit(job)

        self.assertIs(expected_dfr, dfr)
        asyncjob.assert_called_once_with(job)
        self.worklist.push.assert_called_once_with(ajob)
        self.reactor.callLater.assert_called_once_with(
            0, self.dispatcher._execute
        )

    def test__execute_no_jobs(self):
        self.worklist.__len__.return_value = 0
        self.workers.available = True
        dfr = self.dispatcher._execute()
        self.assertIsInstance(dfr, defer.Deferred)
        self.assertIsNone(dfr.result)
        self.worklist.pop.assert_not_called()
        self.reactor.callLater.assert_not_called()

    def test__execute_no_workers(self):
        self.worklist.__len__.return_value = 1
        self.workers.available = False
        dfr = self.dispatcher._execute()
        self.assertIsInstance(dfr, defer.Deferred)
        self.assertIsNone(dfr.result)
        self.worklist.pop.assert_not_called()
        self.reactor.callLater.assert_called_once_with(
            0.1, self.dispatcher._execute
        )

    @patch("{src}.WorkerPoolDispatcher._call_service".format(**PATH))
    def test__execute_success(self, callService):
        ajob = AsyncServiceCallJob(
            ServiceCallJob("service", "localhost", "method", [], {}),
        )
        self.worklist.pop.return_value = ajob
        self.worklist.__len__.return_value = 1

        self.workers.available = True

        dfr = self.dispatcher._execute()

        self.assertIsInstance(dfr, defer.Deferred)
        callService.assert_called_once_with(ajob)
        self.logger.exception.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()
        self.reactor.callLater.assert_called_once_with(
            0.1, self.dispatcher._execute
        )

    @patch("{src}.WorkerPoolDispatcher._call_service".format(**PATH))
    @patch("{src}.WorkerPoolDispatcher._call_listener".format(**PATH))
    def test__execute_with_listeners(self, callListener, callService):
        ajob = AsyncServiceCallJob(
            ServiceCallJob("service", "localhost", "method", [], {}),
        )
        self.worklist.pop.return_value = ajob
        self.worklist.__len__.return_value = 1

        self.workers.available = True

        listener1 = Mock()
        self.dispatcher.onExecute(listener1)
        listener2 = Mock()
        self.dispatcher.onExecute(listener2)

        callListener.side_effect = [defer.succeed(1), defer.succeed(2)]

        dfr = self.dispatcher._execute()

        self.assertIsInstance(dfr, defer.Deferred)
        self.logger.exception.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

        callListener.assert_has_calls(
            (
                call(listener1, ajob.job),
                call(listener2, ajob.job),
            ),
            any_order=True
        )
        callService.assert_called_once_with(ajob)
        self.reactor.callLater.assert_called_once_with(
            0.1, self.dispatcher._execute
        )

    @patch("{src}.WorkerPoolDispatcher._call_service".format(**PATH))
    def test__execute_with_early_error(self, callService):
        self.worklist.__len__.return_value = 1
        self.worklist.pop.side_effect = ValueError("boom")
        self.workers.available = True

        dfr = self.dispatcher._execute()

        self.assertIsInstance(dfr, defer.Deferred)
        callService.assert_not_called()
        self.logger.exception.assert_called_once_with(ANY)
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    @patch("{src}.WorkerPoolDispatcher._call_service".format(**PATH))
    def test__execute_with_late_error(self, callService):
        ajob = AsyncServiceCallJob(
            ServiceCallJob("service", "localhost", "method", [], {}),
        )
        self.worklist.pop.return_value = ajob
        self.worklist.__len__.return_value = 1
        self.workers.available = True
        callService.side_effect = ValueError("boom")

        dfr = self.dispatcher._execute()

        self.assertIsInstance(dfr, defer.Deferred)
        callService.assert_called_once_with(ajob)
        self.logger.exception.assert_called_once_with(ANY)
        self.worklist.pushfront.assert_called_once_with(ajob)
        self.worklist.push.assert_not_called()

    def test__call_service_success(self):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef)
        cm = MagicMock(spec=("__exit__", "__enter__"))
        cm.__enter__.return_value = worker
        self.workers.borrow.return_value = cm

        self.dispatcher._call_service(ajob)

        worker.run.assert_called_once_with(job)
        self.reactor.callLater.assert_called_once_with(
            0, ajob.success, worker.run.return_value
        )
        self.logger.exception.assert_not_called()
        self.logger.error.assert_not_called()
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test__call_service_pbRemoteError(self):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef)
        error = pb.RemoteError("type", "boom", "tb")
        worker.run.side_effect = error
        cm = MagicMock(spec=("__exit__", "__enter__"))
        cm.__enter__.return_value = worker
        self.workers.borrow.return_value = cm

        self.dispatcher._call_service(ajob)

        worker.run.assert_called_once_with(job)
        self.reactor.callLater.assert_called_once_with(0, ajob.failure, error)
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test__call_service_RemoteException(self):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef)
        error = RemoteException("boom", sentinel.traceback)
        worker.run.side_effect = error
        cm = MagicMock(spec=("__exit__", "__enter__"))
        cm.__enter__.return_value = worker
        self.workers.borrow.return_value = cm

        self.dispatcher._call_service(ajob)

        worker.run.assert_called_once_with(job)
        self.reactor.callLater.assert_called_once_with(0, ajob.failure, error)
        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test__call_service_internal_error(self):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef, workerId=1)
        error = ServiceCallError("boom")
        worker.run.side_effect = error
        cm = MagicMock(spec=("__exit__", "__enter__"))
        cm.__enter__.return_value = worker
        self.workers.borrow.return_value = cm
        self.workers.__contains__.return_value = True

        self.dispatcher._call_service(ajob)

        worker.run.assert_called_once_with(job)
        self.assertTrue(self.logger.exception.called)
        self.assertEqual(self.logger.exception.call_count, 1)
        self.logger.error.assert_not_called()

        self.assertTrue(self.reactor.callLater.called)
        self.assertEqual(self.reactor.callLater.call_count, 1)
        args = self.reactor.callLater.call_args[0]
        self.assertEqual(len(args), 3)
        self.assertEqual(args[0], 0)
        self.assertEqual(args[1], ajob.failure)
        self.assertIsInstance(args[2], pb.Error)

        self.worklist.pushfront.assert_not_called()
        self.worklist.push.assert_not_called()

    def test__call_service_bad_worker(self):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef, workerId=1)
        error = ServiceCallError("boom")
        worker.run.side_effect = error
        cm = MagicMock(spec=("__exit__", "__enter__"))
        cm.__enter__.return_value = worker
        self.workers.borrow.return_value = cm
        self.workers.__contains__.return_value = False

        self.dispatcher._call_service(ajob)

        worker.run.assert_called_once_with(job)
        self.logger.error.assert_called_once_with(ANY, worker.workerId, error)
        self.logger.exception.assert_not_called()
        self.reactor.callLater.assert_not_called()
        self.worklist.pushfront.assert_called_once_with(ajob)
        self.worklist.push.assert_not_called()


class StatsMonitorTest(TestCase):

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)
        self.stats = StatsMonitor()
        self.logger = self.getLogger("zenhub", WorkerPoolDispatcher)

    def test_workers(self):
        self.assertIsInstance(self.stats.workers, dict)
        self.assertEqual(len(self.stats.workers), 0)

    def test_jobs(self):
        self.assertIsInstance(self.stats.jobs, dict)
        self.assertEqual(len(self.stats.jobs), 0)

    @patch("{src}.time".format(**PATH))
    def test_monitor_first_time(self, time):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef, workerId=1)

        start = 100
        finish = 200
        time.time.side_effect = (start, finish)

        with self.stats.monitor(worker, ajob) as stats:
            self.assertIs(stats, self.stats)

            self.assertEqual(len(stats.workers), 1)
            self.assertEqual(len(stats.jobs), 1)

            ws = stats.workers[worker.workerId]
            self.assertEqual(ws.status, "Busy")
            self.assertEqual(ws.previdle, 0)
            self.assertTrue(len(ws.description) > 0)
            self.assertEqual(ws.lastupdate, start)

            js = stats.jobs[job.method]
            self.assertEqual(js.count, 1)
            self.assertEqual(js.last_called_time, start)
            self.assertEqual(js.idle_total, 0.0)
            self.assertEqual(js.running_total, 0.0)

        self.assertEqual(len(self.stats.workers), 1)
        self.assertEqual(len(self.stats.jobs), 1)

        ws = self.stats.workers[worker.workerId]
        self.assertEqual(ws.status, "Idle")
        self.assertEqual(ws.previdle, 0)
        self.assertTrue(len(ws.description) > 0)
        self.assertEqual(ws.lastupdate, finish)

        js = self.stats.jobs[job.method]
        self.assertEqual(js.count, 1)
        self.assertEqual(js.last_called_time, finish)
        self.assertEqual(js.idle_total, 0.0)
        self.assertEqual(js.running_total, finish - start)

    @patch("{src}.time".format(**PATH))
    def test_monitor_some_time_later(self, time):
        job = ServiceCallJob("service", "localhost", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        worker = Mock(spec=WorkerRef, workerId=1)

        ws = WorkerStats()
        ws.status = "Idle"
        ws.description = "ignored"
        ws.previdle = 0
        ws.lastupdate = 200.0
        self.stats.workers[worker.workerId] = ws

        js = JobStats()
        js.count = 3
        js.last_called_time = 400.0
        js.idle_total = 150.0
        js.running_total = 300.0
        self.stats.jobs[job.method] = js

        start = 1000
        finish = 1100
        time.time.side_effect = (start, finish)

        with self.stats.monitor(worker, ajob) as stats:
            self.assertIs(stats, self.stats)
            self.assertEqual(len(stats.workers), 1)
            self.assertEqual(len(stats.jobs), 1)

            ws = stats.workers[worker.workerId]
            self.assertEqual(ws.status, "Busy")
            self.assertEqual(ws.previdle, 800.0)
            self.assertTrue(len(ws.description) > 0)
            self.assertEqual(ws.lastupdate, start)

            js = stats.jobs[job.method]
            self.assertEqual(js.count, 4)
            self.assertEqual(js.last_called_time, start)
            self.assertEqual(js.idle_total, 750.0)
            self.assertEqual(js.running_total, 300.0)

        self.assertEqual(len(self.stats.workers), 1)
        self.assertEqual(len(self.stats.jobs), 1)

        ws = self.stats.workers[worker.workerId]
        self.assertEqual(ws.status, "Idle")
        self.assertEqual(ws.previdle, 800.0)
        self.assertTrue(len(ws.description) > 0)
        self.assertEqual(ws.lastupdate, finish)

        js = self.stats.jobs[job.method]
        self.assertEqual(js.count, 4)
        self.assertEqual(js.last_called_time, finish)
        self.assertEqual(js.idle_total, 750.0)
        self.assertEqual(js.running_total, 300.0 + finish - start)


class ServiceCallJobTest(TestCase):

    def test___init__(self):
        name = "name"
        monitor = "monitor"
        method = "method"
        args = tuple()
        kw = {}
        job = ServiceCallJob(name, monitor, method, args, kw)
        self.assertEqual(job.service, name)
        self.assertEqual(job.monitor, monitor)
        self.assertEqual(job.method, method)
        self.assertEqual(job.args, args)
        self.assertEqual(job.kwargs, kw)


class AsyncServiceCallJobTest(TestCase):

    def test___init__(self):
        job = ServiceCallJob("name", "monitor", "method", [], {})
        ajob = AsyncServiceCallJob(job)
        self.assertEqual(job, ajob.job)
        self.assertEqual(job.method, ajob.method)
        self.assertIsInstance(ajob.deferred, defer.Deferred)
        self.assertIsInstance(ajob.recvtime, float)
