#!/usr/bin/env python

import unittest

import common


class Test_MakeTuningParamsIntoVariables(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-february2019.json'
    expected_servicedef = 'zenoss-cse-february2019-addZingEndpointsToZenhubworker.json'
    migration_module_name = 'addZingEndpointsToZenhubworker'
    migration_class_name = 'AddZingEndpointsToZenhubworker'


if __name__ == '__main__':
unittest.main()
