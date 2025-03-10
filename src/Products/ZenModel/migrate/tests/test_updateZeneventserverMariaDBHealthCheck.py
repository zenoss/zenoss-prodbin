#!/usr/bin/env python

import unittest

import common


class Test_updateZeneventserverMariaDBHealthCheck(
    unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that environment variables for mariadb-model and mariadb-events services were added.
    """

    initial_servicedef = 'zenoss-cse-7.0.13.json'
    expected_servicedef = 'zenoss-cse-7.0.13-updateZeneventserverMariaDBHealthCheck.json'
    migration_module_name = 'updateZeneventserverMariaDBHealthCheck'
    migration_class_name = 'UpdateZeneventserverMariaDBHealthCheck'


if __name__ == '__main__':
    unittest.main()
