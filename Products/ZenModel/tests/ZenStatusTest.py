###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import time

from DateTime import DateTime

import Globals

from Products.ZenModel.ZenStatus import ZenAvailability

import pdb

class ZenStatusTest(unittest.TestCase):
    

    def setUp(self):
        self.za = ZenAvailability()

    def tearDown(self):
        self.za = None


    def testIncr(self):
        self.za.incr()
        time.sleep(1.1)
        self.za.incr()
        self.failUnless(self.za.failstart <= DateTime())
        self.failUnless(self.za.todaydown > 0)
        self.failUnless(self.za.status > 0)
        self.failUnless(self.za.failincr <= DateTime())


    def testReset(self):
        self.za.incr()
        time.sleep(1.1)
        self.za.reset()
        self.failUnless(self.za.failstart == 0)
        self.failUnless(self.za.status == 0)
        self.failUnless(self.za.failincr == 0)


    def testStatus(self):
        self.za.incr()
        time.sleep(1.1)
        self.za.incr()
        self.failUnless(self.za.getStatus() > 0)


    def testStatusString(self):
        self.za.incr()
        time.sleep(1.1)
        self.za.incr()
        self.failIf(self.za.getStatusString() == "Up")


    def testAvailPercent(self):
        self.za.incr()
        time.sleep(1.1)
        self.za.incr()
        self.failUnless(99.9 < self.za.getAvailPercent(DateTime()-7) < 100.0)


if __name__ == "__main__":
    unittest.main()
