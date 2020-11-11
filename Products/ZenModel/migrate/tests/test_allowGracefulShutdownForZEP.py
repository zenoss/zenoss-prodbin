#!/usr/bin/env python

from __future__ import absolute_import

import unittest

from . import common


class TestAllowGracefulShutdownForZEP(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether the changes to the zeneventserver service were made.
    """
    initial_servicedef = 'zenoss-cse-7.0.13.json'
    expected_servicedef = 'zenoss-cse-7.0.13-allowGracefulShutdownForZEP.json'
    migration_module_name = 'allowGracefulShutdownForZEP'
    migration_class_name = 'AllowGracefulShutdownForZEP'


if __name__ == '__main__':
    unittest.main()
