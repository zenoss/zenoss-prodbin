#!/usr/bin/env python
import unittest
import common

class test_updateZopeUrl(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3-updateZopeUrl.json'
    migration_module_name = 'updateZopeUrl'
    migration_class_name = 'UpdateZopeUrl'

if __name__ == '__main__':
    unittest.main()
