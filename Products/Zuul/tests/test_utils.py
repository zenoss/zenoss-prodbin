###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
from random import shuffle

from Products.Zuul.utils import LazySortableList

class Item(object):
    def __init__(self, num):
        self.num = num
    def __repr__(self):
        return '<%s>' % self.num


class LazyListTest(unittest.TestCase):
    
    def test_laziness(self):
        s = range(100)
        shuffle(s)
        l = LazySortableList(s)
        self.assertEqual(len(l), 0)

        sslice = s[:10]
        lslice = l[:10]
        self.assertEqual(sslice, lslice)
        # We've only loaded that slice so far
        self.assertEqual(sslice, l.seen)

        sslice = s[5:20]
        lslice = l[5:20]
        self.assertEqual(sslice, lslice)
        self.assertEqual(s[:20], l.seen)

        # Can't do negative
        self.assertRaises(ValueError,lambda:l[-3])

    def test_sorting(self):
        # Not much to test, since it's all default, but we do have
        # the 'orderby' argument.
        from operator import attrgetter
        s = range(100)
        shuffle(s)
        l = LazySortableList(s, cmp=cmp)
        self.assertEqual(l[:], sorted(s, cmp=cmp))

        items = [Item(num=i) for i in s]
        getnum = attrgetter('num')

        l = LazySortableList(items, key=getnum)
        self.assertEqual(l[:], sorted(items, key=getnum))

        l = LazySortableList(items, orderby='num')
        self.assertEqual(l[:], sorted(items, key=getnum))

        l = LazySortableList(items, key=getnum, reverse=True)
        self.assertEqual(l[:], sorted(items, key=getnum, reverse=True))
        
    

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(LazyListTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')