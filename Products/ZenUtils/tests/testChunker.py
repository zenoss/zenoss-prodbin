###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import time
from twisted.trial import unittest
from Products.ZenUtils.zencatalog import chunk, DisconnectedDuringGenerator

class TestChunker(unittest.TestCase):
    def test_chunking(self):
        iterable = range(10)
        results = []
        def callback(result):
            results.append(result)
        def test(ignored):
            self.assertEqual(results, [[0,1,2,3,4,5,6,7],[8,9]])
        c = chunk(iterable, callback, size=8, delay=0)
        return c.addCallback(test)

    def test_chunking_with_raise(self):
        def g():
            for i in range(10):
                try:
                    if not i % 3:
                        raise Exception
                    else:
                        yield i
                except:
                    yield DisconnectedDuringGenerator(i)

        results = []
        def callback(result):
            results.append(result)
        reconnected = []
        def reconnect():
            reconnected.append(True)
        c = chunk(g(), callback, reconnect, size=6, delay=0)
        def test(result):
            self.assertEqual(results, [[0,1,2,3,4,5],[6,7,8,9]])
            self.assertEqual(len(reconnected), 4)
        return c.addCallback(test)

    def test_delay(self):
        times = []
        results = []
        delay = 2

        def g():
            yield 1
            times.append(time.time())
            yield DisconnectedDuringGenerator(0)
            yield 1

        def reconnect():
            times.append(time.time())

        def callback(r):
            results.append(r)

        def test(r):
            delaytime = times[1]-times[0]
            # This is technically iffy, but will only fail if the non-delay
            # part of the iteration takes more than a second. This is
            # incredibly unlikely, so rounding to the second is cool.
            self.assert_(int(delaytime)==delay)
            # Just make sure stuff's in the right order, for fun
            self.assertEqual(results, [[1, 0, 1]])

        c = chunk(g(), callback, reconnect, 3, delay)
        return c.addCallback(test)



