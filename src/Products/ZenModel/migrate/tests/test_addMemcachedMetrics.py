#!/usr/bin/env python
import unittest
import common

class test_addMemcachedMetrics(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3-addMemcachedMetrics.json'
    migration_module_name = 'addMemcachedMetrics'
    migration_class_name = 'addMemcachedMetrics'

if __name__ == '__main__':
    unittest.main()
