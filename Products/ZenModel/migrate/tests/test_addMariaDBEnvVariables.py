#!/usr/bin/env python

import unittest

import common


class test_addMariaDBEnvVariables(
    unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that environment variables for mariadb-model and mariadb-events services were added.
    """

    initial_servicedef = 'zenoss-cse-7.0.16.json'
    expected_servicedef = 'zenoss-cse-7.0.16-addMariaDBEnvVariables.json'
    migration_module_name = 'addMariaDBEnvVariables'
    migration_class_name = 'AddMariaDBEnvVariables'


if __name__ == '__main__':
    unittest.main()
