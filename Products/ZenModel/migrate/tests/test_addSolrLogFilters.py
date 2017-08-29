##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest
from Products.ZenUtils.Utils import zenPath

class test_addSolrLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding LogFilters for Solr logs (ZEN-28097)
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = initial_servicedef        # because addRabbitMQLogFilters doesn't change Service objects
    migration_module_name = 'addSolrLogFilters'
    migration_class_name = 'AddSolrLogFilters'
    expected_log_filters = dict()

    filterName = "solr"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef
