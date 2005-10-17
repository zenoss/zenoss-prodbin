#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import unittest
import transaction

from OFS.Folder import manage_addFolder

from Testing.ZopeTestCase import ZopeLite, connections

from TestSchema import create, build, DataRoot

#ZopeLite.installProduct("ZenRelations")

class RMBaseTest(unittest.TestCase):
    
    def setUp(self):
        self.app = ZopeLite.app()
        dataroot = self.create(self.app, DataRoot, "dataroot")
        dataroot.zPrimaryBasePath = ("",)
        manage_addFolder(self.app, "folder")

    def tearDown(self):
        transaction.abort()
        self.app._p_jar.close()
        self.app = None


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        return create(context, klass, id)

    def build(self, context, klass, id):
        """create instance attache to context and build relationships"""
        return build(context, klass, id)
