import unittest
import common

class Test_updateZopeDeadlockIntervalKillCount(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the 'deadlock_check' healthcheck is changed to all zopes"
    """
    initial_servicedef = 'zenoss-cse-february2019-updateZopeDeadlockMaxtime.json'
    expected_servicedef = 'zenoss-cse-july2019-updateZopeDeadlockIntervalKillCount.json'
    migration_module_name = 'updateZopeDeadlockIntervalKillCount'
    migration_class_name = 'UpdateZopeDeadlockIntervalKillCount'
