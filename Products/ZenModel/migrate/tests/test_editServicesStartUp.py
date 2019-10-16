#!/usr/bin/env python

from __future__ import absolute_import

import unittest

from . import common


class TestUseRabbitmqScriptLauncher(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether services' start up commands are modified"""
    initial_servicedef = 'zenoss-cse-7.0.3-init.json'
    expected_servicedef = 'zenoss-cse-7.0.3-editServicesStartUp.json'
    migration_module_name = 'editServicesStartUp'
    migration_class_name = 'EditServicesStartUp'


if __name__ == '__main__':
    unittest.main()