#!/usr/bin/env python

import os
import unittest
import Globals
import common

class Test_fixNginxPagespeedI18n(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that 'pagespeed on' pagespeed Disallow '*i18n*' is in zproxy's config file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixNginxPagespeedI18n.json'
    migration_module_name = 'fixNginxPagespeedI18n'
    migration_class_name = 'FixNginxPagespeedI18n'


if __name__ == '__main__':
    unittest.main()
