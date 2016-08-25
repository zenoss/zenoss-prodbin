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

class test_updateKibanaInZproxyConf(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating kibana route in zproxy config
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updateKibanaInZproxyConf.json'
    migration_module_name = 'updateKibanaInZproxyConf'
    migration_class_name = 'UpdateKibanaInZproxyConf'