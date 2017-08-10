#!/usr/bin/env python

import os
import unittest

import Globals
import common


class Test_addSolrService(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that missedRuns threshold is added to collector services.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addSolrService.json'
    migration_module_name = 'addSolrService'
    migration_class_name = 'AddSolrService'


if __name__ == '__main__':
    unittest.main()
