#!/usr/bin/env python

import unittest

import common


class Test_AddConfigZenHubWorkerService(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test the AddConfigZenHubWorkerService class."""

    initial_servicedef = 'zenoss-cse-7.0.13.json'
    expected_servicedef = 'zenoss-cse-addConfigZenHubWorkerService.json'
    migration_module_name = 'addConfigZenHubWorkerService'
    migration_class_name = 'AddConfigZenHubWorkerService'


if __name__ == '__main__':
    unittest.main()
