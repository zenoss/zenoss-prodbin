##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_addSessionSvcToApiProxy(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding the Context variable gcp.loadbalancing.gke-ilb.frontend to the top-level service
         and the KEYPROXY_SESSION_SVC environment variable to zing-api-proxy
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330.json'
    expected_servicedef = 'zenoss-cse-7.0.3_330-addSessionSvcToApiProxy.json'
    migration_module_name = 'addSessionSvcToApiProxy'
    migration_class_name = 'AddSessionSvcToApiProxy'

class test_addSessionSvcToApiProxy_noOverwriteExisting(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that we don't overwrite the value of gcp.loadbalancing.gke-ilb.frontend if it already exists
    """
    initial_servicedef = 'zenoss-cse-7.0.3_330-hasGkeIlbValue.json'
    expected_servicedef = 'zenoss-cse-7.0.3_330-hasGkeIlbValue-addSessionSvcToApiProxy.json'
    migration_module_name = 'addSessionSvcToApiProxy'
    migration_class_name = 'AddSessionSvcToApiProxy'