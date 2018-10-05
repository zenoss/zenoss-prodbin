from itertools import chain
from unittest import TestCase

from Products.ZenHub.worklist import (
    ZenHubPriority, ZenHubWorklist,
    _build_weighted_list,
    _message_priority_map,
    _normal_priorities, _no_adm_priorities
)


class ZenHubPriorityTest(TestCase):

    def test_has_required_priority_names(self):
        expected = set(["OTHER", "EVENTS", "MODELING"])
        actual = set(p.name for p in ZenHubPriority)
        self.assertEqual(actual, expected)

    def test_has_required_priority_ordering(self):
        expected = [
            ZenHubPriority.EVENTS,
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

    def test_normal_priorities(self):
        expected = set(ZenHubPriority)
        actual = set(_normal_priorities)
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

    def __init__(self, method):
        self.method = method


class ZenHubWorklistTest(TestCase):

    def setUp(self):
        self.worklist = ZenHubWorklist()

        self.eventJobs = tuple(
            MockJob("sendEvent%s" % ("s" if (n % 2 == 0) else ""))
            for n in range(5)
        )

        self.otherJobs = tuple(
            MockJob("do%s" % ("That" if (n % 2 == 0) else "This"))
            for n in range(5)
        )

        self.admJobs = tuple(MockJob("applyDataMaps") for n in range(5))

        for job in chain(self.eventJobs, self.otherJobs, self.admJobs):
            self.worklist.push(job)

    def test_length(self):
        self.assertEqual(15, len(self.worklist))

    def test_length_of(self):
        wl = self.worklist
        self.assertEqual(5, wl.length_of(ZenHubPriority.EVENTS))
        self.assertEqual(5, wl.length_of(ZenHubPriority.OTHER))
        self.assertEqual(5, wl.length_of(ZenHubPriority.MODELING))

    def test_empty_worklist(self):
        worklist = ZenHubWorklist()
        actual = worklist.pop()
        self.assertEqual(None, actual)

    def test_only_adm_worklist_with_pop_ignore_adm(self):
        worklist = ZenHubWorklist()
        worklist.push(MockJob("applyDataMaps"))
        actual = worklist.pop(allowADM=False)
        self.assertEqual(None, actual)

    def test_normal_pop_order(self):
        expected = [
            self.eventJobs[0],
            self.eventJobs[1], self.otherJobs[0],
            self.eventJobs[2],
            self.eventJobs[3], self.otherJobs[1], self.admJobs[0],
            self.eventJobs[4],
            self.otherJobs[2], self.otherJobs[3],
            self.otherJobs[4], self.admJobs[1],
            self.admJobs[2], self.admJobs[3], self.admJobs[4],
        ]
        actual = []
        while len(self.worklist):
            actual.append(self.worklist.pop())
        self.assertSequenceEqual(expected, actual)

    def test_no_adm_pop_order(self):
        expected = [
            self.eventJobs[0],
            self.eventJobs[1], self.otherJobs[0],
            self.eventJobs[2],
            self.eventJobs[3],
            self.eventJobs[4], self.otherJobs[1],
            self.otherJobs[2], self.otherJobs[3], self.otherJobs[4],
        ]
        actual = []
        while True:
            job = self.worklist.pop(allowADM=False)
            if job is None:
                break
            actual.append(job)
        self.assertSequenceEqual(expected, actual)
