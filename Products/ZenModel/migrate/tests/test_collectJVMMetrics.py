#!/usr/bin/env python

import unittest

import common


class test_collectJVMMetrics(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3-collectJVMMetrics.json'
    migration_module_name = 'collectJVMMetrics'
    migration_class_name = 'CollectJVMMetrics'


if __name__ == '__main__':
    unittest.main()
