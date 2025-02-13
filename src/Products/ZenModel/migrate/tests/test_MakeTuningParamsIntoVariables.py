#!/usr/bin/env python

import unittest

import common


class Test_MakeTuningParamsIntoVariables(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-february2019.json'
    expected_servicedef = 'zenoss-cse-february2019-MakeTuningParamsIntoVariables.json'
    migration_module_name = 'makeTuningParamsIntoVariables'
    migration_class_name = 'MakeTuningParamsIntoVariables'


if __name__ == '__main__':
    unittest.main()
