#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import unittest

from OFS.Folder import manage_addFolder

from Testing.ZopeTestCase import ZopeLite

from Products.ZenRelations.SchemaManager import manage_addSchemaManager

from TestSchema import create, build

class RMBaseTest(unittest.TestCase):
    
    def setUp(self):
        self.app = ZopeLite.app()
        ZopeLite.installProduct("ZenRelations")
        manage_addSchemaManager(self.app)
        self.app.mySchemaManager.loadSchemaFromFile("schema.data")
        manage_addFolder(self.app, "folder")

    def tearDown(self):
        self.app = None

    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        return create(context, klass, id)

    def build(self, context, klass, id):
        """create instance attache to context and build relationships"""
        return build(context, klass, id)
