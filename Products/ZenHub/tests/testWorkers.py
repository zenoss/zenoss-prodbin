##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from random import choice
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenHub.WorkerSelection import InOrderSelection, \
    ReservationAwareSelection, ReversedReservationAwareSelection

class MockWorker(object):
    busy = False

class MockOptions(object):
    workersReservedForEvents = 0

def setupNWorkers(n):
    return [MockWorker() for i in range(n)]

def setupNRandomWorkers(n):
    workers = setupNWorkers(n)
    for w in workers:
        w.busy = choice([True, False])
    return workers

class TestWorkers(BaseTestCase):
    def assertValidSelection(self, workers, selection, options):
        for i in selection:
            self.assertTrue(0 <= i < len(workers))
            if options:
                self.assertTrue(i>=options.workersReservedForEvents)
            self.assertFalse(workers[i].busy)
        unselected = set(range(len(workers)))-set(selection)
        for i in unselected:
            self.assertTrue(workers[i].busy or i<options.workersReservedForEvents)

    def testInOrderSelection(self):
        selector = InOrderSelection()
        options = MockOptions()
        workerGenerators = [setupNWorkers, setupNRandomWorkers]
        for generator in workerGenerators:
            for n in range(16):
                workers = generator(n)
                selection = list(selector.getCandidateWorkerIds(workers, options))
                self.assertValidSelection(workers, selection, options)
                self.assertEqual(selection, sorted(selection))

    def testReservationAwareSelection(self):
        selector = ReservationAwareSelection()
        options = MockOptions()
        options.workersReservedForEvents = 2
        workerGenerators = [setupNWorkers, setupNRandomWorkers]
        for generator in workerGenerators:
            for n in [i+options.workersReservedForEvents for i in range(16)]:
                workers = generator(n)
                selection = list(selector.getCandidateWorkerIds(workers, options))
                self.assertValidSelection(workers, selection, options)
                self.assertEqual(selection, sorted(selection))
        
    def testReversedReservationAwareSelection(self):
        selector = ReversedReservationAwareSelection()
        options = MockOptions()
        options.workersReservedForEvents = 2
        workerGenerators = [setupNWorkers, setupNRandomWorkers]
        for generator in workerGenerators:
            for n in [i+options.workersReservedForEvents for i in range(16)]:
                workers = generator(n)
                selection = list(selector.getCandidateWorkerIds(workers, options))
                self.assertValidSelection(workers, selection, options)
                self.assertEqual(selection, list(reversed(sorted(selection))))
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWorkers))
    return suite
