##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import collections
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenHub.zenhub import _ZenHubWorklist

MockHubWorklistItem = collections.namedtuple('MockHubWorklistItem', 'method value')

class TestWorklist(BaseTestCase):

    def testLen(self):
        worklist = _ZenHubWorklist()
        self.assertEqual(len(worklist), 0)

        for i in range(10):
            worklist.append(MockHubWorklistItem('test', i))
        self.assertEqual(len(worklist), 10)

        for i in range(10,20):
            worklist.append(MockHubWorklistItem('sendEvents', i))
        self.assertEqual(len(worklist), 20)

        for i in range(20,30):
            worklist.append(MockHubWorklistItem('applyDataMaps', i))
        self.assertEqual(len(worklist), 30)

    def testDispatch(self):
        worklist = _ZenHubWorklist()
        self.assertEqual(len(worklist.otherworklist), 0)
        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(10):
            worklist.append(MockHubWorklistItem('test', i))
        self.assertEqual(len(worklist.otherworklist), 10)
        self.assertEqual(len(worklist.eventworklist), 0)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(10,20):
            worklist.append(MockHubWorklistItem('sendEvents', i))
        self.assertEqual(len(worklist.otherworklist), 10)
        self.assertEqual(len(worklist.eventworklist), 10)
        self.assertEqual(len(worklist.applyworklist), 0)

        for i in range(20,30):
            worklist.append(MockHubWorklistItem('applyDataMaps', i))
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

    def testAppend(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.append(MockHubWorklistItem('test', i))
        for i in range(10,20):
            worklist.append(MockHubWorklistItem('sendEvents', i))
        for i in range(20,30):
            worklist.append(MockHubWorklistItem('applyDataMaps', i))
        self.assertEqual([i.value for i in worklist.otherworklist], range(10))
        self.assertEqual([i.value for i in worklist.eventworklist], range(10, 20))
        self.assertEqual([i.value for i in worklist.applyworklist], range(20, 30))

    def testPush(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem('test', i))
        for i in range(10,20):
            worklist.push(MockHubWorklistItem('sendEvents', i))
        for i in range(20,30):
            worklist.push(MockHubWorklistItem('applyDataMaps', i))
        self.assertEqual([i.value for i in worklist.otherworklist], range(9,  -1, -1))
        self.assertEqual([i.value for i in worklist.eventworklist], range(19,  9, -1))
        self.assertEqual([i.value for i in worklist.applyworklist], range(29, 19, -1))

    def testPopAll(self):
        worklist = _ZenHubWorklist()
        for i in range(10):
            worklist.push(MockHubWorklistItem('test', i))
        for i in range(10,20):
            worklist.push(MockHubWorklistItem('sendEvents', i))
        for i in range(20,30):
            worklist.push(MockHubWorklistItem('applyDataMaps', i))
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
            worklist.push(MockHubWorklistItem('sendEvents', i))
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
            worklist.push(MockHubWorklistItem('applyDataMaps', i))
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
            worklist.push(MockHubWorklistItem('test', i))
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
