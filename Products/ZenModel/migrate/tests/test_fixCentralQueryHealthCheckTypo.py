#!/usr/bin/env python

import os
import unittest

import Globals
import common


class Test_FixCentralQueryHealthCheckTypo(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that CentralQuery HealthCheck typo, 'anwering' -> 'answering' has been fixed.
    """
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-fixCentralQueryHealthCheckTypo.json'
    migration_module_name = 'fixCentralQueryHealthCheckTypo'
    migration_class_name = 'FixCentralQueryHealthCheckTypo'


if __name__ == '__main__':
    unittest.main()
