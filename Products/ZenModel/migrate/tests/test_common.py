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
class test_compare_string(unittest.TestCase):
    def test_None(self):
        s1 = "foo"
        s2 = None
        expected = (False, [], compare.Diff(s1, s2))
        self.assertEqual(expected, compare(s1, s2))

    def test_same(self):
        s1 = "foo"
        s2 = "foo"
        expected = (True, None, None)
        self.assertEqual(expected, compare(s1, s2))

    def test_diff(self):
        s1 = "foo"
        s2 = "bar"
        expected = (False, [], compare.Diff(s1, s2))
        self.assertEqual(expected, compare(s1, s2))

    def test_multiline_same(self):
        s1 = "foo\nbar\nbaz\n"
        s2 = "foo\nbar\nbaz\n"
        expected = (True, None, None)
        self.assertEqual(expected, compare(s1, s2))

    def test_multiline_diff(self):
        s1 = "foo\nbar\nbaz\n"
        s2 = "foo\nBAR\nbaz\n"
        expected = (False, [], None)
        actual = compare(s1, s2)
        diff = '\n'.join(actual[-1])
        self.assertEqual(expected[:-1], actual[:-1])
        self.assertIn('-bar', diff)
        self.assertIn('+BAR', diff)


class test_compare_dict(unittest.TestCase):
    def test_none(self):
        d1 = {"a":1, "b":2}
        d2 = None
        expected = (False, [], compare.Diff(d1, d2))
        self.assertEqual(expected, compare(d1, d2))

    def test_same(self):
        d1 = {"a":1, "b":2}
        d2 = {"a":1, "b":2}
        expected = (True, None, None)
        self.assertEqual(expected, compare(d1, d2))

    def test_value(self):
        d1 = {"a":1, "b":2}
        d2 = {"a":1, "b":22}
        expected = (False, ["b"], compare.Diff(d1['b'], d2['b']))
        self.assertEqual(expected, compare(d1, d2))

    def test_size(self):
        d1 = {"a":1, "b":2}
        d2 = {"a":1, "b":2, "c":3}
        expected = (False, ['c'], compare.Diff(compare.missingKey, d2['c']))
        self.assertEqual(expected, compare(d1, d2))

    def test_case_same(self):
        """case insensitive keys, use value of "most-lowercase" key"""
        d1 = dict(AA=1, Aa=2, aA=3, aa=4, bB=6, BB=7)
        d2 = dict(Aa=4, BB=6)
        expected = (True, None, None)
        self.assertEqual(expected, compare(d1, d2))

    def test_case_diff(self):
        """case insensitive keys, use value of "most-lowercase" key"""
        d1 = dict(AA=1, Aa=2, aA=3, aa=22, bB=6, BB=7)
        d2 = dict(Aa=4, BB=6)
        expected = (False, ['aa'], compare.Diff(d1['aa'], d2['Aa']))
        self.assertEqual(expected, compare(d1, d2))


class test_compare_list(unittest.TestCase):
    def test_same(self):
        l1 = [1,2,3]
        l2 = [1,2,3]
        expected = (True, None, None)
        self.assertEqual(expected, compare(l1, l2))

    def test_none(self):
        l1 = [1,2,3]
        l2 = None
        expected = (False, [], compare.Diff(l1, l2))
        self.assertEqual(expected, compare(l1, l2))

    def test_value(self):
        l1 = [1,2,3]
        l2 = [1,22,3]
        expected = (False, [1], compare.Diff(l1[1], l2[1]))
        self.assertEqual(expected, compare(l1, l2))

    def test_size(self):
        l1 = [1,2,3]
        l2 = [1,2]
        expected = (False, [], compare.Diff(l1, l2))
        self.assertEqual(expected, compare(l1, l2))
