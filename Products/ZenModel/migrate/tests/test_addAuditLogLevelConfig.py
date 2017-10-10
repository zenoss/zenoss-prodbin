##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_addAuditLogLevelConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that audit log levev log is added.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addAuditLogLevelConfig.json'
    migration_module_name = 'addAuditLogLevelConfig'
    migration_class_name = 'addAuditLogLevelConfig'


if __name__ == '__main__':
    unittest.main()
