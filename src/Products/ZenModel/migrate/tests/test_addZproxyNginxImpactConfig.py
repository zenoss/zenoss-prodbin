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

class test_addZproxyNginxImpactConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating zproxy configuration for zope upstreams
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-addZproxyNginxImpactConfig.json'
    migration_module_name = 'addZproxyNginxImpactConfig'
    migration_class_name = 'AddZproxyNginxImpactConfig'

if __name__ == '__main__':
    unittest.main()
