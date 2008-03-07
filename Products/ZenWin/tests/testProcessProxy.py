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

import Globals
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import zenPath

from Products.ZenWin.ProcessProxy import ProcessProxy, TimeoutError

TEST_DIR = 'Products/ZenWin/tests'

class TestProcessProxy(BaseTestCase):

    def testProcessProxy(self):
        pp = ProcessProxy(zenPath(TEST_DIR, 'TestClass.py'), 'TestClass')
        pp.start(1, 1, 2, foo='bar')
        self.assert_(pp.boundedCall(1, 'echo', 'test') == (('test',), {}) )
        self.assert_(pp.boundedCall(1, 'getInit') == ((1, 2,), dict(foo='bar') ) )
        try:
            pp.boundedCall(1, 'error', 'hello')
            thrown = None
        except AttributeError, ex:
            thrown = True
        self.assert_(thrown)
        
        pp = ProcessProxy(zenPath(TEST_DIR, 'TestClass.py'), 'TestClass')
        pp.start(1, 1, 2, foo='bar')
        self.assert_(ex.args == ('hello',))
        self.assert_(pp.boundedCall(1, 'sleep', 0.5) == 0.5)
        try:
            thrown = None
            pp.boundedCall(0.5, 'sleep', 0.6)
        except TimeoutError:
            thrown = True
        self.assert_(thrown)
        pp.stop()
            

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestProcessProxy))
    return suite
