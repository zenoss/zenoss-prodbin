#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest
import transaction

from OFS.Folder import manage_addFolder

from Testing.ZopeTestCase import ZopeLite

from Products.ZenModel.DataRoot import DataRoot

from Testing.ZopeTestCase import ZopeLite
from Testing.ZopeTestCase.ZopeTestCase import ZopeTestCase, user_role, \
                                    folder_name, standard_permissions

class ZenModelBaseTest(ZopeTestCase):


    def _setupFolder(self):
        '''Creates and configures the folder.'''
        if self.app._getOb(folder_name, False):
            self.app._delObject(folder_name)
            transaction.commit()
        self.app.manage_addFolder(folder_name)
        self.folder = getattr(self.app, folder_name)
        self.folder._addRole(user_role)
        self.folder.manage_role(user_role, standard_permissions)


    def afterSetUp(self):
        """setup schema manager and add needed permissions"""
        self.app = ZopeLite.app()
        ZopeLite.installProduct("ZenRelations")
        ZopeLite.installProduct("ZenModel")
        ZopeLite.installProduct("ZCatalog")
        ZopeLite.installProduct("ZCTextIndex")
        self.dmd = self.create(self.app, DataRoot, "dmd")
        self.dmd.zPrimaryBasePath = ("",)
        #self.dmd.manage_permission("Add Relationship Managers", [user_role,])
        self.dmd.manage_permission("Add DMD Objects", [user_role,])
        self.dmd.manage_permission("Delete objects", [user_role,])
        self.dmd.manage_permission("Copy or Move", [user_role,])


    def beforeTearDown(self):
        transaction.abort()
        if self.folder._p_jar is not None:
            self.app._delObject(folder_name)
        transaction.commit()
    
    def tearDown(self):
        self.app = None


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst
