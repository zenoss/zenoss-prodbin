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

from ZenModelBaseTest import ZenModelBaseTest

class TestBogusRPNEval(ZenModelBaseTest):

    def testRpn(self):
        from Products.ZenModel.MinMaxThreshold import rpneval
        self.assertEquals(rpneval(2, '2,*'), 4)
        self.assertEquals(rpneval(7, '2,3,*,*'), 42)
        self.assertEquals(rpneval(19, '9,5,/,*,32,+'), 66.2)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestBogusRPNEval))
    return suite
        
