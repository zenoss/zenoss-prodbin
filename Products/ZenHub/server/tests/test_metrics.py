##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from collections import defaultdict
from unittest import TestCase
from mock import call, Mock, patch, sentinel

from ..config import legacy_metric_priority_map
from ..metrics import (
    _CallStats,
    _CountKey,
    _legacy_metric_worklist_total,
    decrementLegacyMetricCounters,
    handleServiceCallCompleted,
    handleServiceCallReceived,
    handleServiceCallStarted,
    IHubServerConfig,
    IMetricManager,
    incrementLegacyMetricCounters,
    register_legacy_worklist_metrics,
    ServiceCallPriority,
    ServiceCallCompleted,
    ServiceCallReceived,
    ServiceCallStarted,
)

PATH = {"src": "Products.ZenHub.server.metrics"}


class LegacyMetricsTest(TestCase):
    """Test for legacy metrics."""

    @patch("{src}.registry".format(**PATH), autospec=True)
    @patch("{src}.Metrology".format(**PATH), autospec=True)
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_metrology_registration(
        self, _counters, _getUtility, _Metrology, _registry,
    ):
        config = Mock()
        config.legacy_metric_priority_map = legacy_metric_priority_map
        _getUtility.return_value = config
        counter = _Metrology.counter
        metrics = {}
        _registry.metrics = metrics

        eventCounter = sentinel.eventCounter
        admCounter = sentinel.admCounter
        singleAdmCounter = sentinel.singleAdmCounter
        otherCounter = sentinel.otherCounter
        totalCounter = sentinel.totalCounter

        def map_gauge_to_inputs(key):
            return {
                "zenhub.eventWorkList": eventCounter,
                "zenhub.admWorkList": admCounter,
                "zenhub.otherWorkList": otherCounter,
                "zenhub.singleADMWorkList": singleAdmCounter,
                _legacy_metric_worklist_total: totalCounter,
            }[key]

        counter.side_effect = map_gauge_to_inputs

        expected_counter_calls = [
            call("zenhub.eventWorkList"),
            call("zenhub.admWorkList"),
            call("zenhub.otherWorkList"),
            call("zenhub.singleADMWorkList"),
            call(_legacy_metric_worklist_total),
        ]

        expected_counter_contents = {
            ServiceCallPriority.EVENTS: eventCounter,
            ServiceCallPriority.MODELING: admCounter,
            ServiceCallPriority.OTHER: otherCounter,
            ServiceCallPriority.SINGLE_MODELING: singleAdmCounter,
            "total": totalCounter,
        }

        register_legacy_worklist_metrics()

        _getUtility.assert_called_once_with(IHubServerConfig)
        self.assertEqual(len(expected_counter_calls), len(counter.mock_calls))
        counter.assert_has_calls(expected_counter_calls, any_order=True)

        self.assertEqual(len(expected_counter_calls), len(_counters))
        self.assertDictEqual(expected_counter_contents, _counters)

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_incrementCounters(self, _counters):
        event = Mock(spec=["priority"])
        pcounter = Mock(spec=["increment"])
        tcounter = Mock(spec=["increment"])
        _counters[event.priority] = pcounter
        _counters["total"] = tcounter

        incrementLegacyMetricCounters(event)

        pcounter.increment.assert_called_once_with()
        tcounter.increment.assert_called_once_with()
        self.assertListEqual(
            sorted([event.priority, "total"]),
            sorted(_counters.keys()),
        )

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_skip_decrement(self, _counters):
        event = Mock(spec=["retry"])
        event.retry = object()

        decrementLegacyMetricCounters(event)

        self.assertDictEqual({}, _counters)

    @patch("{src}._legacy_worklist_counters".format(**PATH), new_callable=dict)
    def test_decrementCounters(self, _counters):
        event = Mock(spec=["priority", "retry"])
        event.retry = None
        pcounter = Mock(spec=["decrement", "count"])
        tcounter = Mock(spec=["decrement", "count"])
        pcounter.count = 0
        tcounter.count = 0
        _counters[event.priority] = pcounter
        _counters["total"] = tcounter

        decrementLegacyMetricCounters(event)

        pcounter.decrement.assert_called_once_with()
        tcounter.decrement.assert_called_once_with()
        self.assertListEqual(
            sorted([event.priority, "total"]),
            sorted(_counters.keys()),
        )


class ServiceCallMetricsTest(TestCase):
    """Test the ServiceCall metrics handling."""

    def setUp(self):
        _patchables = (
            ("_task_stats", defaultdict(_CallStats)),
            ("_servicecall_count", defaultdict(int)),
            ("_servicecall_wip", defaultdict(int)),
            ("getUtility", Mock(spec=[])),
        )
        for name, value in _patchables:
            patcher = patch(
                "{src}.{name}".format(src=PATH["src"], name=name),
                new=value,
            )
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_handleServiceCallReceived(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallReceived)
        event.timestamp = 100.0
        key = _CountKey(event)

        handleServiceCallReceived(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(event.timestamp, self._task_stats[event.id].received)
        self.assertEqual(0.0, self._task_stats[event.id].started)
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, self._servicecall_count[key])
        self.assertEqual(0, len(self._servicecall_wip))
        writer.write_metric.assert_called_once_with(
            "zenhub.servicecall.count",
            1,
            event.timestamp * 1000,
            {
                "queue": event.queue,
                "priority": event.priority.name,
                "service": event.service,
                "method": event.method,
            },
        )

    def test_handleServiceCallStarted(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallStarted)
        event.timestamp = 100.0
        key = _CountKey(event)

        handleServiceCallStarted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0.0, self._task_stats[event.id].received)
        self.assertEqual(event.timestamp, self._task_stats[event.id].started)
        self.assertEqual(0, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(1, self._servicecall_wip[key])
        writer.write_metric.assert_called_once_with(
            "zenhub.servicecall.wip",
            1,
            event.timestamp * 1000,
            {
                "queue": event.queue,
                "priority": event.priority.name,
                "service": event.service,
                "method": event.method,
            },
        )

    def test_handleServiceCallCompleted_success(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(0, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls((
            call(
                "zenhub.servicecall.wip",
                0,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.cycletime",
                10000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                    "status": "success",
                },
            ),
            call(
                "zenhub.servicecall.count",
                0,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.leadtime",
                60000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
        ), any_order=True)

    def test_handleServiceCallCompleted_retry(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = object()
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(1, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(1, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls((
            call(
                "zenhub.servicecall.wip",
                0,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.cycletime",
                10000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                    "status": "retry",
                },
            ),
        ), any_order=True)

    def test_handleServiceCallCompleted_failure(self):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = object()
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0
        self._servicecall_count[key] += 1
        self._servicecall_wip[key] += 1

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(0, self._servicecall_count[key])
        self.assertEqual(0, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls((
            call(
                "zenhub.servicecall.wip",
                0,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.cycletime",
                10000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                    "status": "failure",
                },
            ),
            call(
                "zenhub.servicecall.count",
                0,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.leadtime",
                60000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
        ), any_order=True)

    @patch("{src}.log".format(**PATH), autospec=True)
    def test_negative_values(self, _log):
        writer = self.getUtility.return_value.metric_writer
        event = Mock(spec=ServiceCallCompleted)
        event.timestamp = 160.0
        event.error = None
        event.retry = None
        key = _CountKey(event)
        self._task_stats[event.id].received = 100.0
        self._task_stats[event.id].started = 150.0

        handleServiceCallCompleted(event)

        self.getUtility.assert_called_once_with(IMetricManager)
        self.assertEqual(0, len(self._task_stats))
        self.assertEqual(1, len(self._servicecall_count))
        self.assertEqual(1, len(self._servicecall_wip))
        self.assertEqual(-1, self._servicecall_count[key])
        self.assertEqual(-1, self._servicecall_wip[key])
        writer.write_metric.assert_has_calls((
            call(
                "zenhub.servicecall.wip",
                -1,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.cycletime",
                10000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                    "status": "success",
                },
            ),
            call(
                "zenhub.servicecall.count",
                -1,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
            call(
                "zenhub.servicecall.leadtime",
                60000,
                160000,
                {
                    "queue": event.queue,
                    "priority": event.priority.name,
                    "service": event.service,
                    "method": event.method,
                },
            ),
        ), any_order=True)
        self.assertEqual(2, _log.warn.call_count)
