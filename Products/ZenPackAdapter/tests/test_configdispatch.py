#!/usr/bin/env python

##############################################################################
#
# Copyright (C) Zenoss, Inc. 2021, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import time
import Globals
from collections import Counter

from Products.ZenUtils.Utils import unused
from Testing import ZopeTestCase

from Products.ZenPackAdapter.configdispatch import WorkerPool

unused(Globals)


def makeoptions(type_, id_):
    return {
        "zpaCollectorType": type_,
        "zpaCollectorId": id_
    }

zenpython = makeoptions("zenpython", None)

# just 50 random words to use as device IDs in tests
wordlist = [
    "soothe", "astonishing", "religion", "swift", "scissors", "parsimonious",
    "robust", "visitor", "humdrum", "boil", "grouchy", "lumber", "stare",
    "nasty", "malicious", "puncture", "change", "disturbed", "hobbies",
    "educate", "imagine", "able", "sail", "long-term", "familiar", "annoy",
    "assorted", "arch", "screeching", "stale", "selection", "energetic",
    "self", "crabby", "past", "invite", "wander", "legal", "cherries",
    "doubt", "literate", "stimulating", "smell", "short", "next", "salty",
    "magnificent", "flower", "billowy", "plucky"
]

class TestConfigDispatch(ZopeTestCase.ZopeTestCase):

    def setUp(self):
        self.pool = WorkerPool()

    def test_add_workers(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))
        self.pool.add_worker(makeoptions("zenpython",  "c12346"))
        self.pool.add_worker(makeoptions("zenpython",  "c12347"))
        self.pool.add_worker(makeoptions("zenmodeler", "c12348"))

        self.assertEqual(len(self.pool.get_workers("zenpython")), 3)
        self.assertEqual(len(self.pool.get_workers("zenmodeler")), 1)

        #  duplicate, so should not add anything
        self.pool.add_worker(makeoptions("zenmodeler", "c12348"))
        self.assertEqual(len(self.pool.get_workers("zenpython")), 3)

    def test_remove_workers(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))
        self.assertEqual(len(self.pool.get_workers("zenpython")), 1)
        self.pool.remove_worker(makeoptions("zenpython",  "c12345"))
        self.assertEqual(len(self.pool.get_workers("zenpython")), 0)
        self.pool.remove_worker(makeoptions("zenpython",  "c12345"))
        self.assertEqual(len(self.pool.get_workers("zenpython")), 0)

    def test_device_singlecollector(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))
        collectorA = self.pool.collectorId_for_deviceId("deviceA", zenpython)
        self.assertEqual(collectorA, "c12345")

    def test_device_multicollector(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12341"))
        self.pool.add_worker(makeoptions("zenpython",  "c12342"))
        self.pool.add_worker(makeoptions("zenpython",  "c12343"))
        self.pool.add_worker(makeoptions("zenpython",  "c12344"))
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))
        count = Counter()
        collectorA = self.pool.collectorId_for_deviceId("deviceA", zenpython)
        self.assertIsNotNone(collectorA)
        count[collectorA] += 1
        collectorB = self.pool.collectorId_for_deviceId("deviceB", zenpython)
        self.assertIsNotNone(collectorB)
        count[collectorB] += 1
        collectorC = self.pool.collectorId_for_deviceId("deviceC", zenpython)
        self.assertIsNotNone(collectorC)
        count[collectorC] += 1
        collectorD = self.pool.collectorId_for_deviceId("deviceD", zenpython)
        self.assertIsNotNone(collectorD)
        count[collectorD] += 1

        # devices were assigned to more than one collector.  If they
        # all got put on one, either we're hashing really poorly, or
        # there is a bug.
        self.assertTrue(len(count) > 1)


    def test_scaleup(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12341"))
        self.pool.add_worker(makeoptions("zenpython",  "c12342"))
        self.pool.add_worker(makeoptions("zenpython",  "c12343"))

        collectors = {}
        for d in wordlist:
            collectors[d] = self.pool.collectorId_for_deviceId(d, zenpython)

        self.pool.add_worker(makeoptions("zenpython",  "c12344"))
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))
        collectors2 = {}
        moves = 0
        for d in wordlist:
            collectors2[d] = self.pool.collectorId_for_deviceId(d, zenpython)
            if collectors2[d] != collectors[d]:
                moves += 1

        # Some rebalancing is fine, but it shouldn't be excessive.
        self.assertTrue(moves < len(wordlist) / (2.0/5.0))

    def test_scaledown(self):
        self.pool.add_worker(makeoptions("zenpython",  "c12341"))
        self.pool.add_worker(makeoptions("zenpython",  "c12342"))
        self.pool.add_worker(makeoptions("zenpython",  "c12343"))
        self.pool.add_worker(makeoptions("zenpython",  "c12344"))
        self.pool.add_worker(makeoptions("zenpython",  "c12345"))

        collectors = {}
        for d in wordlist:
            collectors[d] = self.pool.collectorId_for_deviceId(d, zenpython)

        self.pool.remove_worker(makeoptions("zenpython",  "c12344"))
        self.pool.remove_worker(makeoptions("zenpython",  "c12345"))

        collectors2 = {}
        for d in wordlist:
            collectors2[d] = self.pool.collectorId_for_deviceId(d, zenpython)
            if collectors2[d] != collectors[d]:
                # Only devices previously on the collectors we removed
                # should be remapped to another.
                self.assertIn(collectors[d], ["c12344", "c12345"])

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestConfigDispatch))
    return suite


if __name__ == "__main__":
    from zope.testrunner.runner import Runner
    runner = Runner(found_suites=[test_suite()])
    runner.run()


