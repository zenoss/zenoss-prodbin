##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_updateHbaseLogPath(unittest.TestCase):
    """
    Tests for the testing harness
    """
    def test_compare_dicts(self):
        d  = {"a":1, "b":2}
        d1 = {"a":1, "b":22}
        d2 = {"a":1, "b":2, "c":3}
        self.assertEqual((True, None, None), common.compare(d, d))
        self.assertEqual((False, [], None), common.compare(d, None))
        self.assertEqual((False, ['b'], None), common.compare(d, d1))
        self.assertEqual((False, ['c'], None), common.compare(d, d2))

    def test_compare_lists(self):
        l  = [1,2,3]
        l1 = [1,4,3]
        l2 = [1,2,3,4]
        self.assertEqual((True, None, None), common.compare(l, l))
        self.assertEqual((False, [], None), common.compare(l, None))
        self.assertEqual((False, [1], None), common.compare(l, l1))
        self.assertEqual((False, [], None), common.compare(l, l2))
