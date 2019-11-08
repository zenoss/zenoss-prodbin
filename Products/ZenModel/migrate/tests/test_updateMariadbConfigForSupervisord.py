#!/usr/bin/env python

import unittest

import common


class Test_updateMariadbConfigForSupervisord(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = \
        'zenoss-cse-7.0.3-updateMariadbConfigForSupervisord.json'
    migration_module_name = 'updateMariadbConfigForSupervisord'
    migration_class_name = 'UpdateMariadbConfigForSupervisord'


if __name__ == '__main__':
    unittest.main()
