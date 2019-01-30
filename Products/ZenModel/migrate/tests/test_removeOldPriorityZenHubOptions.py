#!/usr/bin/env python

import unittest

import common


class Test_removeOldPriorityZenHubOptions(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330.json'
    expected_servicedef = 'zenoss-cse-7.0.3_330-removeOldPriorityZenHubOptions.json'
    migration_module_name = 'removeOldPriorityZenHubOptions'
    migration_class_name = 'RemoveOldPriorityZenHubOptions'


if __name__ == '__main__':
    unittest.main()
