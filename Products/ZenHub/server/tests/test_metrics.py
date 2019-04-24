##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase, skip
from mock import Mock, patch, sentinel

# from ..metrics import (
#     register_metrics_on_worklist,
#     PriorityListLengthGauge, WorklistLengthGauge,
# )

PATH = {"src": "Products.ZenHub.server"}


class JunkTest(TestCase):
    """Junk."""

    @skip("Not testing string formatting")
    @patch("{src}.StatsMonitor".format(**PATH), autospec=True)
    @patch("{src}.get_worklist_metrics".format(**PATH), autospec=True)
    def test_getStatusReport(self, getWorklistMetrics, statsMonitor):
        gauges = {
            ZenHubPriority.EVENTS: 3404,
            ZenHubPriority.OTHER: 276,
            ZenHubPriority.MODELING: 169,
            ZenHubPriority.SINGLE_MODELING: 23,
        }
        now = time.time() - (1350)
        workTracker = {
            0: WorkerStats(
                "Busy", "localhost:EventServer:sendEvent", now, 34.8,
            ),
            1: WorkerStats(
                "Idle", "localhost:SomeService:someMethod", now, 4054.3,
            ),
            2: None,
        }
        execTimer = {
            "sendEvent": Mock(
                JobStats,
                count=2953, idle_total=3422.3, running_total=35.12,
                last_called_time=now,
            ),
            "sendEvents": Mock(
                JobStats,
                count=451, idle_total=3632.5, running_total=20.5,
                last_called_time=now,
            ),
            "applyDataMaps": Mock(
                JobStats,
                count=169, idle_total=620.83, running_total=3297.248,
                last_called_time=now,
            ),
            "singleApplyDataMaps": Mock(
                JobStats,
                count=23, idle_total=1237.345, running_total=936.85,
                last_called_time=now,
            ),
            "someMethod": Mock(
                JobStats,
                count=276, idle_total=7384.3, running_total=83.3,
                last_called_time=now,
            ),
        }
        getWorklistMetrics.return_value = gauges
        stats = statsMonitor.return_value
        stats.workers = workTracker
        stats.jobs = execTimer
        manager = HubServiceManager(
            modeling_pause_timeout=self.modeling_pause_timeout,
            passwordfile=self.passwordfile,
            pbport=self.pbport,
            xmlrpcport=self.xmlrpcport,
        )
        print manager.getStatusReport()


# class StatsMonitorTest(TestCase):  # noqa: D101
#
#     def setUp(self):
#         self.getLogger_patcher = patch(
#             "{src}.getLogger".format(**PATH), autospec=True,
#         )
#         self.getLogger = self.getLogger_patcher.start()
#         self.addCleanup(self.getLogger_patcher.stop)
#         self.stats = StatsMonitor()
#         self.logger = self.getLogger("zenhub", WorkerPoolExecutor)
#
#     def test_workers(self):
#         self.assertIsInstance(self.stats.workers, dict)
#         self.assertEqual(len(self.stats.workers), 0)
#
#     def test_jobs(self):
#         self.assertIsInstance(self.stats.jobs, dict)
#         self.assertEqual(len(self.stats.jobs), 0)
#
#     @patch("{src}.time".format(**PATH))
#     def test_monitor_first_time(self, time):
#         call = ServiceCall("service", "localhost", "method", [], {})
#         task = ServiceCallTask("queue", call)
#         worker = Mock(spec=WorkerRef, workerId=1)
#
#         start = 100
#         finish = 200
#         time.time.side_effect = (start, finish)
#
#         with self.stats.monitor(worker, task) as stats:
#             self.assertIs(stats, self.stats)
#
#             self.assertEqual(len(stats.workers), 1)
#             self.assertEqual(len(stats.jobs), 1)
#
#             ws = stats.workers[worker.workerId]
#             self.assertEqual(ws.status, "Busy")
#             self.assertEqual(ws.previdle, 0)
#             self.assertGreater(len(ws.description), 0)
#             self.assertEqual(ws.lastupdate, start)
#
#             js = stats.jobs[call.method]
#             self.assertEqual(js.count, 1)
#             self.assertEqual(js.last_called_time, start)
#             self.assertEqual(js.idle_total, 0.0)
#             self.assertEqual(js.running_total, 0.0)
#
#         self.assertEqual(len(self.stats.workers), 1)
#         self.assertEqual(len(self.stats.jobs), 1)
#
#         ws = self.stats.workers[worker.workerId]
#         self.assertEqual(ws.status, "Idle")
#         self.assertEqual(ws.previdle, 0)
#         self.assertGreater(len(ws.description), 0)
#         self.assertEqual(ws.lastupdate, finish)
#
#         js = self.stats.jobs[call.method]
#         self.assertEqual(js.count, 1)
#         self.assertEqual(js.last_called_time, finish)
#         self.assertEqual(js.idle_total, 0.0)
#         self.assertEqual(js.running_total, finish - start)
#
#     @patch("{src}.time".format(**PATH))
#     def test_monitor_some_time_later(self, time):
#         call = ServiceCall("service", "localhost", "method", [], {})
#         task = ServiceCallTask("queue", call)
#         worker = Mock(spec=WorkerRef, workerId=1)
#
#         ws = WorkerStats()
#         ws.status = "Idle"
#         ws.description = "ignored"
#         ws.previdle = 0
#         ws.lastupdate = 200.0
#         self.stats.workers[worker.workerId] = ws
#
#         js = JobStats()
#         js.count = 3
#         js.last_called_time = 400.0
#         js.idle_total = 150.0
#         js.running_total = 300.0
#         self.stats.jobs[call.method] = js
#
#         start = 1000
#         finish = 1100
#         time.time.side_effect = (start, finish)
#
#         with self.stats.monitor(worker, task) as stats:
#             self.assertIs(stats, self.stats)
#             self.assertEqual(len(stats.workers), 1)
#             self.assertEqual(len(stats.jobs), 1)
#
#             ws = stats.workers[worker.workerId]
#             self.assertEqual(ws.status, "Busy")
#             self.assertEqual(ws.previdle, 800.0)
#             self.assertGreater(len(ws.description), 0)
#             self.assertEqual(ws.lastupdate, start)
#
#             js = stats.jobs[call.method]
#             self.assertEqual(js.count, 4)
#             self.assertEqual(js.last_called_time, start)
#             self.assertEqual(js.idle_total, 750.0)
#             self.assertEqual(js.running_total, 300.0)
#
#         self.assertEqual(len(self.stats.workers), 1)
#         self.assertEqual(len(self.stats.jobs), 1)
#
#         ws = self.stats.workers[worker.workerId]
#         self.assertEqual(ws.status, "Idle")
#         self.assertEqual(ws.previdle, 800.0)
#         self.assertGreater(len(ws.description) > 0)
#         self.assertEqual(ws.lastupdate, finish)
#
#         js = self.stats.jobs[call.method]
#         self.assertEqual(js.count, 4)
#         self.assertEqual(js.last_called_time, finish)
#         self.assertEqual(js.idle_total, 750.0)
#         self.assertEqual(js.running_total, 300.0 + finish - start)


class MetrologySupportTest(TestCase):
    """Test Metrology support."""

    @skip("needs priority fix")
    def test_has_required_metric_mapping(self):
        expected_mapping = {
            "zenhub.eventWorkList": ZenHubPriority.EVENTS,
            "zenhub.admWorkList": ZenHubPriority.MODELING,
            "zenhub.otherWorkList": ZenHubPriority.OTHER,
            "zenhub.singleADMWorkList": ZenHubPriority.SINGLE_MODELING,
        }
        for metric, actual in _gauge_priority_map.iteritems():
            expected = expected_mapping.get(metric)
            self.assertEqual(
                actual, expected,
                "Metric '%s' should map to %s, not %s" % (
                    metric, expected.name, actual.name
                )
            )

    @skip("needs priority fix")
    @patch("{src}.registry".format(**PATH), {})
    @patch("{src}.Metrology".format(**PATH), autospec=True)
    @patch("{src}.PriorityListLengthGauge".format(**PATH))
    @patch("{src}.WorklistLengthGauge".format(**PATH))
    def test_metrology_registration(self, wgauge, pgauge, metro):

        eventGauge = sentinel.eventGauge
        admGauge = sentinel.admGauge
        singleAdmGauge = sentinel.singleAdmGauge
        otherGauge = sentinel.otherGauge
        totalGauge = wgauge.return_value

        def map_gauge_to_inputs(worklist, priority):
            return {
                ZenHubPriority.EVENTS: eventGauge,
                ZenHubPriority.MODELING: admGauge,
                ZenHubPriority.OTHER: otherGauge,
                ZenHubPriority.SINGLE_MODELING: singleAdmGauge,
            }[priority]

        pgauge.side_effect = map_gauge_to_inputs
        wgauge.return_value = totalGauge

        worklist = ZenHubWorklist()
        register_metrics_on_worklist(worklist)

        expected_pgauge_calls = [
            call(worklist, ZenHubPriority.EVENTS),
            call(worklist, ZenHubPriority.MODELING),
            call(worklist, ZenHubPriority.SINGLE_MODELING),
            call(worklist, ZenHubPriority.OTHER),
        ]
        self.assertEqual(len(expected_pgauge_calls), len(pgauge.mock_calls))
        pgauge.assert_has_calls(expected_pgauge_calls, any_order=True)
        wgauge.assert_called_once_with(worklist)

        metro_gauge_calls = [
            call("zenhub.eventWorkList", eventGauge),
            call("zenhub.admWorkList", admGauge),
            call("zenhub.singleADMWorkList", singleAdmGauge),
            call("zenhub.otherWorkList", otherGauge),
            call("zenhub.workList", totalGauge),
        ]
        self.assertEqual(len(metro_gauge_calls), len(metro.gauge.mock_calls))
        metro.gauge.assert_has_calls(metro_gauge_calls, any_order=True)

    @skip("needs priority fix")
    def test_gauges(self):
        worklist = ZenHubWorklist()

        pg1 = PriorityListLengthGauge(worklist, ZenHubPriority.EVENTS)
        pg2 = PriorityListLengthGauge(worklist, ZenHubPriority.MODELING)
        pg3 = PriorityListLengthGauge(worklist, ZenHubPriority.OTHER)
        wg = WorklistLengthGauge(worklist)

        eventJob1 = MockJob("sendEvent")
        eventJob2 = MockJob("sendEvent")
        eventJob3 = MockJob("sendEvent")
        admJob = MockJob("applyDataMaps")
        otherJob1 = MockJob("doThis")
        otherJob2 = MockJob("doThat")

        worklist.push(eventJob1)
        worklist.push(eventJob2)
        worklist.push(eventJob3)
        worklist.push(admJob)
        worklist.push(otherJob1)
        worklist.push(otherJob2)

        self.assertEqual(pg1.value, 3)
        self.assertEqual(pg2.value, 1)
        self.assertEqual(pg3.value, 2)
        self.assertEqual(wg.value, 6)
