#!/usr/bin/env python

import os
import unittest
import Globals
import common

<<<<<<< HEAD
class Test_EnableNginxPagespeed(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that 'pagespeed on' is in zproxy's config file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5-pagespeedoff.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5.json-enableNginxPagespeed.json'
    migration_module_name = 'enableNginxPagespeed'
    migration_class_name = 'EnableNginxPagespeed'
=======
class Test_fixNginxPagespeedI18n(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that 'pagespeed on' pagespeed Disallow '*i18n*' is in zproxy's config file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixNginxPagespeedI18n.json'
    migration_module_name = 'fixNginxPagespeedI18n'
    migration_class_name = 'FixNginxPagespeedI18n'
>>>>>>> ZEN-24758-migration


if __name__ == '__main__':
    unittest.main()
