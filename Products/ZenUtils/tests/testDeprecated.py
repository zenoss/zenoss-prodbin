###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""
Note that this is meant to be run from zopecctl using the "test" option.
If you would like to run these tests from python, simply do the following:
    python Products/ZenUtils/tests/testDeprecated.py
"""

import unittest
import os
import os.path
import Globals
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import zenPath  # TODO: this test shouldn't rely on zenPath
from Products.ZenUtils.deprecated import deprecated, DeprecatedLogger

TEST_LOGFILE = 'dEpReCaTeD.TeStLoG'  # something unique


@deprecated
def add(x, y):
    return x + y


class TestDeprecated(BaseTestCase):
    """Test @deprecated in Development mode and Release mode."""

    #Enable logging for these tests
    disableLogging = False

    def _doesLogFileExist(self, deleteIt=False):
        filepath = zenPath('log', TEST_LOGFILE)
        exists = os.path.isfile(filepath)
        if exists and deleteIt:
            os.unlink(filepath)
            self.assertFalse(os.path.isfile(filepath))
        return exists

    def afterSetUp(self):
        super(TestDeprecated, self).afterSetUp()
        self.oldDevMode = Globals.DevelopmentMode
        self._doesLogFileExist(deleteIt=True)

    def testReleaseMode(self):
        Globals.DevelopmentMode = False
        DeprecatedLogger.config(repeat=True,
                                fileName=TEST_LOGFILE,  # should be ignored
                                propagate=False)        # quiet
        self.assertEqual(add(3, 6), 9)
        self.assertFalse(self._doesLogFileExist())

    def testDevModeNoLog(self):
        Globals.DevelopmentMode = True
        DeprecatedLogger.config(repeat=True,
                                fileName=None,    # no file
                                propagate=False)  # quiet
        self.assertEqual(add(5, 8), 13)
        self.assertFalse(self._doesLogFileExist())

    def testDevModeWithLog(self):
        Globals.DevelopmentMode = True
        DeprecatedLogger.config(repeat=True,
                                fileName=TEST_LOGFILE,  # should create it
                                propagate=False)        # quiet
        self.assertEqual(add(4, 7), 11)
        self.assertTrue(self._doesLogFileExist())
        with open(zenPath('log', TEST_LOGFILE)) as f:
            self.assertTrue('Call to deprecated function add' in f.read())

    def beforeTearDown(self):
        Globals.DevelopmentMode = self.oldDevMode
        self._doesLogFileExist(deleteIt=True)
        super(TestDeprecated, self).beforeTearDown()


def test_suite():
    return unittest.makeSuite(TestDeprecated)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
