#!/usr/bin/env python

import unittest

import common


class test_addZingEndpointsToZenHubWorkerADM(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-cse-pre-addZingEndpointsToZenHubWorkerADM.json'
    expected_servicedef = 'zenoss-cse-post-addZingEndpointsToZenHubWorkerADM.json'
    migration_module_name = 'addZingEndpointsToZenHubWorkerADM'
    migration_class_name = 'AddZingEndpointsToZenhubWorkerADM'


if __name__ == '__main__':
    unittest.main()
