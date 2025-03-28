#!/usr/bin/env python

from __future__ import absolute_import

import unittest

from . import common


class TestUseRabbitmqScriptLauncher(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether the new rabbitmq.sh script is installed.
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3-useRabbitmqScriptLauncher.json'
    migration_module_name = 'useRabbitmqScriptLauncher'
    migration_class_name = 'UseRabbitmqScriptLauncher'


if __name__ == '__main__':
    unittest.main()
