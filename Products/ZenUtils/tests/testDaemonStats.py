##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import unittest, os

from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class DaemonStatsTest(BaseTestCase):
    """Test the DaemonStats"""

    def setUp(self):
        self.daemon_stats = DaemonStats()

    def testDaemonsTagsServiceId(self):
        os.environ["CONTROLPLANE"] = "1"
        os.environ["CONTROLPLANE_SERVICE_ID"] = "ID"
        self.daemon_stats.config( "name", "monitor", None, None, None)
        self.assertEqual(
             {'daemon': 'name', 'internal': True, 'monitor': 'monitor', 'metricType': 'type', 'serviceId': 'ID'},
            self.daemon_stats._tags("type")
        )

    def testDaemonsDoesNotTagServiceId(self):
        if "CONTROLPLANE" in os.environ:
            del os.environ["CONTROLPLANE"]

        if "CONTROLPLANE_SERVICE_ID" in os.environ:
            del os.environ["CONTROLPLANE_SERVICE_ID"]

        self.daemon_stats.config( "name", "monitor", None, None, None)
        self.assertEqual(
             {'daemon': 'name', 'internal': True, 'monitor': 'monitor', 'metricType': 'type'},
            self.daemon_stats._tags("type")
        )

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(DaemonStatsTest),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
