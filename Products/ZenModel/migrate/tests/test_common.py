##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Tests for the testing harness
"""

import unittest
from common import compare


class test_compare_dict(unittest.TestCase):
    def test_value(self):
        d1 = {"a":1, "b":2}
        d2 = {"a":1, "b":22}
        expected = (False, ["b"], None)
        self.assertEqual(expected, compare(d1, d2))

    def test_size(self):
        d1 = {"a":1, "b":2}
        d2 = {"a":1, "b":2, "c":3}
        expected = (False, ["c"], None)
        self.assertEqual(expected, compare(d1, d2))
