import unittest
import common

class Test_addZopeDeadlockHC(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the 'deadlock_check' healthcheck is added to all zopes"
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330.json'
    expected_servicedef = 'zenoss-cse-7.0.3_330-addZopeDeadlockHC.json'
    migration_module_name = 'addZopeDeadlockHC'
    migration_class_name = 'AddZopeDeadlockHC'
