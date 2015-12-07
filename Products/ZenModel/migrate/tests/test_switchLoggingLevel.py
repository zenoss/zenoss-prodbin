#!/usr/bin/env python

import os
import unittest

import Globals
import common


class Test_SwitchLoggingLevel(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that logging level is switched to WARN.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-switchLoggingLevel.json'
    migration_module_name = 'switchLoggingLevel'
    migration_class_name = 'SwitchLoggingLevel'


if __name__ == '__main__':
    unittest.main()

