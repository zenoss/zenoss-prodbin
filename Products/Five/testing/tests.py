##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Tests for the testing framework.

$Id: tests.py 60620 2005-10-21 18:07:37Z yuppie $
"""
import os
import sys
import unittest
from Products.Five.testing import doctest, testrunner

def test_suite():
    return unittest.TestSuite((
        doctest.DocTestSuite('Products.Five.testing.renormalizing'),
        doctest.DocFileSuite('formparser.txt'),
        doctest.DocTestSuite('Products.Five.testing.loggingsupport'),
        testrunner.test_suite(),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
