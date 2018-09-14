##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_addBlockBasicAuthNonCSE(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the addBlockBasicAuth migration does nothing to a non-cse install.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0.json'
    migration_module_name = 'addBlockBasicAuth'
    migration_class_name = 'AddBlockBasicAuth'
