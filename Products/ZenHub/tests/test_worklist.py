from itertools import chain
from mock import patch, call, MagicMock
from unittest import TestCase

from Products.ZenHub.worklist import (
    ZenHubPriority, ZenHubWorklist, _PrioritySelection,
    _build_weighted_list,
    _message_priority_map,
    _all_priorities, _no_adm_priorities,
    register_metrics_on_worklist, _gauge_priority_map,
    PriorityListLengthGauge, WorklistLengthGauge
)

PATH = {'src': 'Products.ZenHub.worklist'}


class MetrologySupportTest(TestCase):

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

    @patch("{src}.registry".format(**PATH), {})
    @patch("{src}.Metrology".format(**PATH), autospec=True)
    @patch("{src}.PriorityListLengthGauge".format(**PATH))
    @patch("{src}.WorklistLengthGauge".format(**PATH))
    def test_metrology_registration(self, wgauge, pgauge, metro):

        eventGauge = MagicMock()
        admGauge = MagicMock()
        singleAdmGauge = MagicMock()
        otherGauge = MagicMock()
        totalGauge = MagicMock()

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


class ZenHubPriorityTest(TestCase):

    def test_has_required_priority_names(self):
        expected = set(["OTHER", "EVENTS", "SINGLE_MODELING", "MODELING"])
        actual = set(p.name for p in ZenHubPriority)
        self.assertEqual(actual, expected)

    def test_has_required_priority_ordering(self):
        expected = [
            ZenHubPriority.EVENTS,
            ZenHubPriority.SINGLE_MODELING,
            ZenHubPriority.OTHER,
            ZenHubPriority.MODELING,
        ]
        actual = list(sorted(ZenHubPriority))
        self.assertEqual(actual, expected)


class MessagePriorityMapTest(TestCase):

    def test_has_required_message_mapping(self):
        expected_mapping = {
            "sendEvent": ZenHubPriority.EVENTS,
            "sendEvents": ZenHubPriority.EVENTS,
            "applyDataMaps": ZenHubPriority.MODELING,
            "doThis": ZenHubPriority.OTHER,
            "doThat": ZenHubPriority.OTHER
        }
        for mesg, expected in expected_mapping.iteritems():
            actual = _message_priority_map.get(mesg)
            self.assertEqual(
                actual, expected,
                "Message '%s' should map to %s, not %s" % (
                    mesg, expected.name, actual.name
                )
            )


class PriorityListTest(TestCase):

    def test_all_priorities(self):
        expected = set(ZenHubPriority)
        actual = set(_all_priorities)
        self.assertSetEqual(expected, actual)

    def test_no_adm_priorities(self):
        expected = set([ZenHubPriority.EVENTS, ZenHubPriority.OTHER])
        actual = set(_no_adm_priorities)
        self.assertSetEqual(expected, actual)


class BuildPriorityListTest(TestCase):

    def test_one_priority(self):
        expected = (1,)
        actual = _build_weighted_list([1])
        self.assertSequenceEqual(expected, actual)

    def test_two_priorities(self):
        expected = (1, 1, 2, 1)
        actual = _build_weighted_list([1, 2])
        self.assertSequenceEqual(expected, actual)

    def test_three_priorities(self):
        expected = (
            1, 1, 2, 1,
            1, 2, 3,
            1, 1, 2, 1
        )
        actual = _build_weighted_list([1, 2, 3])
        self.assertSequenceEqual(expected, actual)

    def test_four_priorities(self):
        expected = (
            1, 1, 2, 1,
            1, 2, 3,
            1, 1, 2, 1,
            1, 2, 3, 4,
            1, 1, 2, 1,
            1, 2, 3,
            1, 1, 2, 1
        )
        actual = _build_weighted_list([1, 2, 3, 4])
        self.assertSequenceEqual(expected, actual)


class MockJob(object):

    def __init__(self, method, priorityName=None):
        self.method = method
        self.p = priorityName

    def __repr__(self):
        if self.p:
            return "<%s %0x>" % (self.p, id(self))
        return super(MockJob, self).__repr__()


class ZenHubWorklistTest(TestCase):

    def setUp(self):
        self.worklist = ZenHubWorklist()

        self.p1 = tuple(
            MockJob("sendEvent%s" % ("s" if (n % 2 == 0) else ""), "p1")
            for n in range(5)
        )

        self.p3 = tuple(
            MockJob("do%s" % ("That" if (n % 2 == 0) else "This"), "p3")
            for n in range(5)
        )

        self.p4 = tuple(MockJob("applyDataMaps", "p4") for n in range(5))

        self.p2 = tuple(MockJob("singleApplyDataMaps", "p2") for n in range(5))

        for job in chain(self.p1, self.p3, self.p4, self.p2):
            self.worklist.push(job)

    def test_length(self):
        self.assertEqual(20, len(self.worklist))

    def test_length_of(self):
        wl = self.worklist
        self.assertEqual(5, wl.length_of(ZenHubPriority.EVENTS))
        self.assertEqual(5, wl.length_of(ZenHubPriority.OTHER))
        self.assertEqual(5, wl.length_of(ZenHubPriority.MODELING))
        self.assertEqual(5, wl.length_of(ZenHubPriority.SINGLE_MODELING))

    def test_empty_worklist(self):
        worklist = ZenHubWorklist()

        expected_len = 0
        actual_len = len(worklist)
        self.assertEqual(expected_len, actual_len)
        self.assertEqual(None, worklist.pop())

    def test_modeling_paused(self):

        paused = {"state": False}

        def is_paused():
            return paused["state"]

        worklist = ZenHubWorklist(modeling_paused=is_paused)
        for job in chain(self.p1, self.p3, self.p4, self.p2):
            worklist.push(job)

        expected = [
            self.p1[0], self.p1[1], self.p2[0], self.p1[2], self.p1[3],
        ]
        actual = [worklist.pop() for _ in range(len(expected))]
        self.assertListEqual(expected, actual)

        paused["state"] = True

        expected = [
            self.p1[4], self.p3[0], self.p3[1], self.p3[2], self.p3[3],
            self.p3[4], None
        ]
        actual = [worklist.pop() for _ in range(len(expected))]
        self.assertListEqual(expected, actual)

        paused["state"] = False

        expected = [
            self.p2[1], self.p2[2], self.p2[3], self.p4[0], self.p2[4],
            self.p4[1], self.p4[2], self.p4[3], self.p4[4], None
        ]
        actual = [worklist.pop() for _ in range(len(expected))]
        self.assertListEqual(expected, actual)


class TestPrioritySelection(TestCase):

    def setUp(self):
        self.all = _PrioritySelection(_all_priorities)
        self.some = _PrioritySelection(_no_adm_priorities)

    def test_priorities_property(self):
        self.assertSequenceEqual(_all_priorities, self.all.priorities)
        self.assertSequenceEqual(_no_adm_priorities, self.some.priorities)

    def test_all_sequence_order(self):
        p1 = ZenHubPriority.EVENTS
        p2 = ZenHubPriority.SINGLE_MODELING
        p3 = ZenHubPriority.OTHER
        p4 = ZenHubPriority.MODELING
        expected = (
            p1, p1, p2, p1,
            p1, p2, p3,
            p1, p1, p2, p1,
            p1, p2, p3, p4,
            p1, p1, p2, p1,
            p1, p2, p3,
            p1, p1, p2, p1
        )
        actual = [next(self.all) for _ in range(len(expected))]
        self.assertSequenceEqual(expected, actual)

    def test_some_sequence_order(self):
        p1 = ZenHubPriority.EVENTS
        p3 = ZenHubPriority.OTHER
        expected = (
            p1, p1, p3, p1,
            p1, p1, p3, p1
        )
        actual = [next(self.some) for _ in range(len(expected))]
        self.assertSequenceEqual(expected, actual)
