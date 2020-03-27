import Globals
import unittest
import common


class Test_addGlobalConfToMariadb(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """

    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-addGlobalConfToMariadb.json'
    migration_module_name = 'addGlobalConfToMariadb'
    migration_class_name = 'AddGlobalConfToMariadb'


if __name__ == '__main__':
    unittest.main()
