import unittest
import common

class Test_updateZopeDeadlockMaxtime(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the 'deadlock_check' healthcheck is added to all zopes"
    """
    initial_servicedef = 'zenoss-cse-february2019.json'
    expected_servicedef = 'zenoss-cse-february2019-updateZopeDeadlockMaxtime.json'
    migration_module_name = 'updateZopeDeadlockMaxtime'
    migration_class_name = 'UpdateZopeDeadlockMaxtime'
