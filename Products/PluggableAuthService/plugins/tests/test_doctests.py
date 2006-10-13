##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest
from Testing import ZopeTestCase

ZopeTestCase.installProduct('PythonScripts')
ZopeTestCase.installProduct('PluginRegistry')
ZopeTestCase.installProduct('PluggableAuthService')
ZopeTestCase.installProduct('GenericSetup')

def test_suite():
    suite = unittest.TestSuite()
    package = 'Products.PluggableAuthService.plugins.tests'
    tests = [
        ZopeTestCase.FunctionalDocFileSuite('ChallengeProtocolChooser.txt',
                                            package=package),
        ]
    for t in tests:
        suite.addTest(t)
    return suite
