#!/usr/bin/env python

import unittest
import common


class Test_addDBMetrics(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-february2019.json'
    expected_servicedef = 'zenoss-cse-february2019-addDBMetrics.json'
    migration_module_name = 'addDBMetrics'
    migration_class_name = 'addDBMetrics'


if __name__ == '__main__':
    unittest.main()
