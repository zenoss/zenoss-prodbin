# tests/test_updateMemcachedMaxConn.py

import unittest

import common

class Test_updateMemcachedMaxConnOrigConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-updateMemcachedMaxConn.json'
    migration_module_name = 'updateMemcachedMaxConn'
    migration_class_name = 'updateMemcachedMaxConn'
