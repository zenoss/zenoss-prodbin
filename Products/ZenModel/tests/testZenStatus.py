###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import time
import unittest

from DateTime import DateTime

import Globals

from Products.ZenModel.ZenStatus import ZenAvailability
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest

class TestZenStatus(ZenModelBaseTest):
    

    def afterSetUp(self):
        super(TestZenStatus, self).afterSetUp()
        self.za = ZenAvailability()

    def beforeTearDown(self):
        self.za = None
        super(TestZenStatus, self).beforeTearDown()

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

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestZenStatus))
    return suite

if __name__=="__main__":
    framework()
