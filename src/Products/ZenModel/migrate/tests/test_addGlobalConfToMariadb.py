#!/usr/bin/env python

import unittest

import common


class Test_addGlobalConfToMariadb(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """

    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3.json-addGlobalConfToMariadb.json'
    migration_module_name = 'addGlobalConfToMariadb'
    migration_class_name = 'AddGlobalConfToMariadb'


if __name__ == '__main__':
    unittest.main()
