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
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestImportEverything(BaseTestCase):

    def testImportEverything(self):
        import os
        from Products.ZenUtils.Utils import zenPath
        modules = ['ZenModel', 'ZenRelations', 'ZenRRD', 'ZenUtils',
                   'ZenEvents', 'ZenHub']
        for module in modules:
            for fs, ds, d in os.walk(zenPath('Products', module)):
                for f in fs:
                    if f.endswith('.py'):
                        f = f[-2]
                        __import__('Products.%s.%s' % (module, f))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestImportEverything))
    return suite
