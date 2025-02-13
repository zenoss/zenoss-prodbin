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

class test_addBlockBasicAuth(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding the block for basic auth through the GLB and disable the basic
    auth login page.
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330.json'
    expected_servicedef = 'zenoss-cse-7.0.3_330-addBlockAPIBasicAuth.json'
    migration_module_name = 'addBlockAPIBasicAuth'
    migration_class_name = 'AddBlockAPIBasicAuth'
