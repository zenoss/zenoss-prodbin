import unittest
import common


class Test_AddZingConfigToZep (unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the zeneventserver config has zenoss cloud related configs added.
    """
    initial_servicedef = 'zenoss-cse-7.0.3.json'
    expected_servicedef = 'zenoss-cse-7.0.3-addZingConfigToZep.json'
    migration_module_name = 'addZingConfigToZep'
    migration_class_name = 'AddZingConfigToZep'
