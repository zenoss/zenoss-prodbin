###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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
