from unittest import TestCase
from mock import Mock, patch, create_autospec, ANY

from Products.ZenHub.tests.mock_interface import create_interface_mock
from Products.ZenCollector.daemon import (
    CollectorDaemon,
    ICollectorPreferences,
    ITaskSplitter,
    IConfigurationListener,
    Failure,
    defer,
)


class TestCollectorDaemon_maintenanceCycle(TestCase):
    def setUp(t):
        # Patch out the  __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            CollectorDaemon, "__init__", autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        preferences = create_interface_mock(ICollectorPreferences)()
        taskSplitter = create_interface_mock(ITaskSplitter)()
        configurationListener = create_interface_mock(IConfigurationListener)()

        t.cd = CollectorDaemon(
            preferences, taskSplitter, configurationListener
        )
        t.cd.log = Mock(name="log")
        t.cd._prefs = Mock(
            name="options",
            spec_set=["pauseUnreachableDevices"],
            pauseUnreachableDevices=True,
        )
        t.cd.options = Mock(name="options", spec_set=["cycle"], cycle=True)
        t.cd.getDevicePingIssues = create_autospec(t.cd.getDevicePingIssues)
        t.cd._unresponsiveDevices = set()

    def test__maintenanceCycle(t):
        ret = t.cd._maintenanceCycle()

        t.cd.log.debug.assert_called_with(
            "deviceIssues=%r", t.cd.getDevicePingIssues.return_value
        )
        t.assertEqual(ret.result, t.cd.getDevicePingIssues.return_value)

    def test_ignores_unresponsive_devices(t):
        t.cd.log = Mock(name="log")
        t.cd._prefs.pauseUnreachableDevices = False

        ret = t.cd._maintenanceCycle()

        t.assertEqual(ret.result, None)

    def test_no_cycle_option(t):
        t.cd.log = Mock(name="log")
        t.cd._prefs.pauseUnreachableDevices = False
        t.cd.options.cycle = False

        ret = t.cd._maintenanceCycle()

        t.assertEqual(ret.result, "No maintenance required")

    def test_handle_getDevicePingIssues_exception(t):
        t.cd.getDevicePingIssues.side_effect = Exception

        ret = t.cd._maintenanceCycle()

        t.assertIsInstance(ret.result, Failure)
        t.assertIsInstance(ret.result.value, Exception)

    def test_handle__pauseUnreachableDevices_exception(t):
        t.cd._pauseUnreachableDevices = create_autospec(
            t.cd._pauseUnreachableDevices
        )
        t.cd._pauseUnreachableDevices.side_effect = Exception

        ret = t.cd._maintenanceCycle()

        t.assertIsInstance(ret.result, Failure)
        t.assertIsInstance(ret.result.value, Exception)

    def test__pauseUnreachableDevices(t):
        t.cd._scheduler = Mock(
            name="_scheduler",
            spec_set=["resumeTasksForConfig", "pauseTasksForConfig"],
        )
        t.cd._unresponsiveDevices = {"d1", "d2"}
        issues = tuple((d, "count", "total") for d in ["d2", "d3"])
        t.cd.getDevicePingIssues.return_value = issues

        ret = t.cd._pauseUnreachableDevices()

        t.cd._scheduler.resumeTasksForConfig.assert_called_with("d1")
        t.cd._scheduler.pauseTasksForConfig.assert_called_with("d3")
        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, issues)

    def test_writeMetric(t):
        # FIX ME: these attributes are set in the subclass PBDaemon
        # and default to None in the parent, making it non-functional/testable
        from Products.ZenUtils.metricwriter import DerivativeTracker
        from Products.ZenUtils.metricwriter import ThresholdNotifier

        t.cd._derivative_tracker = DerivativeTracker()
        t.cd._threshold_notifier = Mock(ThresholdNotifier)
        t.cd._metric_writer = Mock(name="MetricWriter")

        t.cd.should_trace_metric = create_autospec(t.cd.should_trace_metric)
        t.cd.should_trace_metric.return_value = True

        # First we have to prime the agrogator with an inital value
        metric = "some_metric"
        contextKey = "contextKey"
        contextUUID = "contextUUID"
        tags = {
            "mtrace": ANY,
            "contextUUID": contextUUID,
            "key": contextKey,
        }

        # now it will calculate the deltas
        cases = [
            {"timestamp": 0, "value": 1, "delta": 0.0, "call": False},
            {"timestamp": 1, "value": 100, "delta": 99.0, "call": True},
            {"timestamp": 2, "value": 200, "delta": 100, "call": True},
            # a reset happens
            {"timestamp": 3, "value": 100, "delta": -100, "call": False},
            {"timestamp": 4, "value": 200, "delta": 100, "call": True},
            {"timestamp": 5, "value": 300, "delta": 100, "call": True},
            {"timestamp": 6, "value": 30000, "delta": 29700.0, "call": True},
        ]

        for case in cases:
            ret = t.cd.writeMetric(
                contextKey=contextKey,
                metric=metric,
                value=case["value"],
                metricType="COUNTER",
                contextId="contextId",
                contextUUID=contextUUID,
                timestamp=case["timestamp"],
                min="U",
                max="U",
            )

            t.assertEqual(ret.result, None)  # triggers the callback
            if case["call"]:
                t.cd._metric_writer.write_metric.assert_called_with(
                    metric, case["delta"], case["timestamp"], tags
                )
            t.cd._metric_writer.write_metric.reset_mock()
