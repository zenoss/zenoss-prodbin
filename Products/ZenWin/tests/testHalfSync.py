###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from time import sleep

from Products.ZenWin.HalfSync import HalfSync, TimeoutError, TooManyThreads

class TestHalfSync(BaseTestCase):

    def testBoundedCall(self):
        obj = HalfSync()
        self.assert_(obj.boundedCall(0.2, sleep, 0.1) == None)
        thrown = False
        try:
            obj.boundedCall(0.1, sleep, 0.2)
        except TimeoutError:
            thrown = True
        self.assert_(thrown)
        obj = HalfSync(1)
        thrown = False
        try:
            for i in range(3):
                try:
                    obj.boundedCall(0.01, sleep, 0.2)
                except TimeoutError:
                    pass
        except TooManyThreads:
            thrown = True
        self.assert_(thrown)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestHalfSync))
    return suite
