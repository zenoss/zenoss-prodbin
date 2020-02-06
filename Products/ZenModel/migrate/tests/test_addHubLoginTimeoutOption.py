##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import unittest

import Globals
import common

class Test_AddHubLoginTimeoutOption(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that daemon configuration files now have the hubLoginTimeout option.
    """

    initial_servicedef = 'zenoss-resmgr-6.3.2.json'
    expected_servicedef = 'zenoss-resmgr-6.3.2-addHubLoginTimeoutOption.json'
    migration_module_name = 'addHubLoginTimeoutOption'
    migration_class_name = 'AddHubLoginTimeoutOption'
