#!/usr/bin/env python

import unittest

import common


class Test_setRedisMemory(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-february2019.json'
    expected_servicedef = 'zenoss-cse-february2019-setRedisMemory.json'
    migration_module_name = 'setRedisMemory'
    migration_class_name = 'setRedisMemory'


if __name__ == '__main__':
    unittest.main()
