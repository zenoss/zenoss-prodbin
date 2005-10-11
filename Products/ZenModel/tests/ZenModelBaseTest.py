#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import unittest

from OFS.Folder import manage_addFolder

from Testing.ZopeTestCase import ZopeLite

from Products.ZenModel.DataRoot import DataRoot

class ZenModelBaseTest(unittest.TestCase):
    
    def setUp(self):
        self.app = ZopeLite.app()
        ZopeLite.installProduct("ZenRelations")
        ZopeLite.installProduct("ZenModel")
        ZopeLite.installProduct("ZCatalog")
        ZopeLite.installProduct("ZCTextIndex")
        self.dmd = self.create(self.app, DataRoot, "dmd")
        self.dmd.zPrimaryBasePath = ("","dmd")

    def tearDown(self):
        self.app = None

    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst
