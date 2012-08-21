##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import collections
import heapq
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenHub.zenhub import _ZenHubWorklist

MockHubWorklistItem = collections.namedtuple('MockHubWorklistItem', 'value method')

class TestWorklist(BaseTestCase):

    def testLen(self):
        worklist = _ZenHubWorklist()
        self.assertEqual(len(worklist), 0)

        for i in range(10):
            worklist.append(MockHubWorklistItem(method='test', value=i))
        self.assertEqual(len(worklist), 10)

        for i in range(10,20):
            worklist.append(MockHubWorklistItem(method='sendEvents', value=i))
        self.assertEqual(len(worklist), 20)

        for i in range(20,30):
            worklist.append(MockHubWorklistItem(method='applyDataMaps', value=i))
        self.assertEqual(len(worklist), 30)

    def testDispatch(self):
        worklist = _ZenHubWorklist()
        self.assertEqual(len(worklist.otherworklist), 0)
        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(10):
            worklist.append(MockHubWorklistItem(method='test', value=i))
        self.assertEqual(len(worklist.otherworklist), 10)
        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(10,20):
            worklist.append(MockHubWorklistItem(method='sendEvents', value=i))
        self.assertEqual(len(worklist.otherworklist), 10)
        self.assertEqual(len(worklist.eventworklist), 10)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(20,30):
            worklist.append(MockHubWorklistItem(method='applyDataMaps', value=i))
        self.assertEqual(len(worklist.otherworklist), 10)
        self.assertEqual(len(worklist.eventworklist), 10)
        self.assertEqual(len(worklist.applyworklist), 10)

    def testGetItem(self):
        worklist = _ZenHubWorklist()
        self.assertEqual(worklist.otherworklist, worklist['test'])
        self.assertEqual(worklist.otherworklist, worklist[''])
        self.assertEqual(worklist.otherworklist, worklist[None])
        self.assertEqual(worklist.otherworklist, worklist[47])
        self.assertEqual(worklist.otherworklist, worklist[False])

        self.assertEqual(worklist.eventworklist, worklist['sendEvents'])

        self.assertEqual(worklist.applyworklist, worklist['applyDataMaps'])

    def _popSorted(self, heap):
        return (heapq.heappop(heap) for i in range(len(heap)))

    def testAppend(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.append(MockHubWorklistItem(method='test', value=i))
        for i in range(10,20):
            worklist.append(MockHubWorklistItem(method='sendEvents', value=i))
        for i in range(20,30):
            worklist.append(MockHubWorklistItem(method='applyDataMaps', value=i))
        self.assertEqual([i.value for i in self._popSorted(worklist.otherworklist)], range(10))
        self.assertEqual([i.value for i in self._popSorted(worklist.eventworklist)], range(10, 20))
        self.assertEqual([i.value for i in self._popSorted(worklist.applyworklist)], range(20, 30))

    def testReAppend(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem(method='test', value=i))
        popped = []
        for i in range(5):
            popped.append(worklist.pop())
        for item in popped:
            worklist.push(item)
        self.assertEqual([i.value for i in self._popSorted(worklist.otherworklist)], range(10))

        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem(method='sendEvents', value=i))
        for i in range(5):
            popped.append(worklist.pop())
        for item in popped:
            worklist.push(item)
        self.assertEqual([i.value for i in self._popSorted(worklist.eventworklist)], range(10))

        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem(method='applyDataMaps', value=i))
        for i in range(5):
            popped.append(worklist.pop())
        for item in popped:
            worklist.push(item)
        self.assertEqual([i.value for i in self._popSorted(worklist.applyworklist)], range(10))

    def testPopAll(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem(method='test', value=i))
        for i in range(10,20):
            worklist.push(MockHubWorklistItem(method='sendEvents', value=i))
        for i in range(20,30):
            worklist.push(MockHubWorklistItem(method='applyDataMaps', value=i))
        while worklist:
            job = worklist.pop()
            self.assertIsInstance(job, MockHubWorklistItem)
            self.assertTrue(0 <= job.value < 30)

        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist.otherworklist), 0)
        self.assertEqual(len(worklist.applyworklist), 0)
        self.assertEqual(len(worklist), 0)

    def testPopEventsOnly(self):
        worklist = _ZenHubWorklist()
        for i in range(10,20):
            worklist.push(MockHubWorklistItem(method='sendEvents', value=i))
        while worklist:
            job = worklist.pop()
            self.assertIsNotNone(job)
            self.assertIsInstance(job, MockHubWorklistItem)
            self.assertTrue(10 <= job.value < 20)
        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist), 0)

    def testPopApplyOnly(self):
        worklist = _ZenHubWorklist()
        for i in range(20,30):
            worklist.push(MockHubWorklistItem(method='applyDataMaps', value=i))
        while worklist:
            job = worklist.pop()
            self.assertIsNotNone(job)
            self.assertIsInstance(job, MockHubWorklistItem)
            self.assertTrue(20 <= job.value < 30)
        self.assertEqual(len(worklist.applyworklist), 0)
        self.assertEqual(len(worklist), 0)

    def testPopOtherOnly(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem(method='test', value=i))
        while worklist:
            job = worklist.pop()
            self.assertIsNotNone(job)
            self.assertIsInstance(job, MockHubWorklistItem)
            self.assertTrue(0 <= job.value < 10)
        self.assertEqual(len(worklist.otherworklist), 0)
        self.assertEqual(len(worklist), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWorklist))
    return suite
