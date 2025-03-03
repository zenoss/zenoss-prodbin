##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
import subprocess

from Products.ZenTestCase.BaseTestCase import BaseTestCase


def _startswithInList(testString, listToTest):
    """
    Checks each element in listToTest to see if any one of them
    starts with testString.
    """
    for e in listToTest:
        if testString.startswith(e):
            return True
    return False


class CmdLineProgs(BaseTestCase):
    """
    Test the shipping command line tools and make sure they
    don't stack trace.
    """

    def testZenpackCmd(self):
        cmd = subprocess.check_call(["zenpack", "--list"])  # noqa: S607 S603
        self.assertEqual(
            cmd, 0, "zenpack --list should return 0 exit code; got %d" % cmd
        )


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(CmdLineProgs),))


if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
