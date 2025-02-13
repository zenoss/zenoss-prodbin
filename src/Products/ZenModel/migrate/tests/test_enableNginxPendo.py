#!/usr/bin/env python

import unittest

import common


class test_EnableNginxPendo(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330.json'
    expected_servicedef = 'zenoss-cse-enableNginxPendo.json'
    migration_module_name = 'enableNginxPendo'
    migration_class_name = 'EnableNginxPendo'


if __name__ == '__main__':
    unittest.main()
