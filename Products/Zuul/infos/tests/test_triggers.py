##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.Zuul.infos.triggers import NotificationWindowInfo
from Products.ZenModel.NotificationSubscriptionWindow import (
    NotificationSubscriptionWindow
)


class NotificationWindowInfoTest(BaseTestCase):

    def afterSetUp(self):
        super(NotificationWindowInfoTest, self).afterSetUp()

    def test_start_time(self):
        '''Ensure that the notification window infos
        returns the attributes expected by the UI
        '''

        window = NotificationSubscriptionWindow('window_id')
        setattr(window, 'start', 1506243600)

        window_info = NotificationWindowInfo(window)

        self.assertEqual(window_info.start_ts, 1506243600)
        # ensure original date/time behavior for backwards compatibility
        self.assertEqual(window_info.start, "09/24/2017")
        self.assertEqual(window_info.starttime, "09:00")


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(NotificationWindowInfoTest),
    ))


if __name__ == "__main__":
    unittest.main(defaultTest='test_suite')
