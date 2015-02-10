##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import time
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils import Time


class TestTime(BaseTestCase):
    """
    Tests some of the time utility functions in Products/ZenUtils/Time.py
    """

    def testConvertingTime(self):
        stamp = time.time()
        chicago_time = Time.convertTimestampToTimeZone(stamp, "America/Chicago", "%H")
        new_york_time = Time.convertTimestampToTimeZone(stamp, "America/New_York", "%H")
        if int(chicago_time) != 12:
            self.assertEquals(int(new_york_time), int(chicago_time) +1)

    def testInvalidTimeZoneGivesServerTime(self):
        """
        Make sure we don't stack trace if a user gets an invalid timestamp set.
        """
        stamp = time.time()
        current_time = Time.convertTimestampToTimeZone(stamp, "pepe", fmt="%H")
        server_time = Time.isoDateTime(stamp, fmt="%H")
        self.assertEquals(current_time, server_time)
        
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestTime))
    return suite

