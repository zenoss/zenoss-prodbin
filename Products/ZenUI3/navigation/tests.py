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

from zope.testing import doctestunit
from zope.component import testing
from Testing import ZopeTestCase as ztc

def test_suite():
    return unittest.TestSuite([

        # Unit tests for your API
        #doctestunit.DocFileSuite(
        #    'README.txt', package='Products.ZenUI3.navigation',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

        #doctestunit.DocTestSuite(
        #    module='Products.ZenUI3.mymodule',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

         #Integration tests that use ZopeTestCase
        ztc.ZopeDocFileSuite(
            'README.txt', package='Products.ZenUI3.navigation',
            setUp=testing.setUp, tearDown=testing.tearDown),

        #ztc.FunctionalDocFileSuite(
        #    'browser.txt', package='Products.ZenUI3'),

        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
