
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_disableZproxyAccessLog(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the zserver-threads is commented out
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-disableZproxyAccessLog.json'
    migration_module_name = 'disableZproxyAccessLog'
    migration_class_name = 'DisableZproxyAccessLog'
