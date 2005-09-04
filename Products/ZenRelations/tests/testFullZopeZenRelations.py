#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

from Testing.ZopeTestCase import ZopeLite
from Testing.ZopeTestCase.ZopeTestCase import ZopeTestCase, user_role
from TestSchema import *

from Products.ZenRelations.SchemaManager import manage_addSchemaManager
from Products.ZenRelations.Exceptions import *

class FullZopeTestCases(ZopeTestCase):

    def beforeSetUp(self):
        """install ZenRelations need to do before setup because commit happes"""
        ZopeLite.installProduct("ZenRelations")


    def afterSetUp(self):
        """setup schema manager and add needed permissions"""
        manage_addSchemaManager(self.folder)
        self.folder.mySchemaManager.loadSchemaFromFile("schema.data")
        self.folder.manage_permission("Add Relationship Managers", [user_role,])
        self.folder.manage_permission("Delete objects", [user_role,])
        self.folder.manage_addFolder("subfolder")


    def testRenameToMany(self):
        """test renaming an object that has a tomany relationship"""
        dev = build(self.folder, Device, "dev")
        anna = build(self.folder, Location, "anna")
        dev.location.addRelation(anna)
        self.failUnless(dev.location() == anna)
        self.folder.manage_renameObject("dev", "newdev")
        self.failUnless(hasattr(self.folder, "newdev"))
        self.failUnless(hasattr(anna.devices, "newdev"))
        self.failIf(hasattr(anna.devices, "dev"))


    def testCutPasteRM(self):
        """test cut and past of a RM make sure primarypath is set properly"""
        dev = build(self.folder, Device, "dev")
        cookie = self.folder.manage_cutObjects( ids=('dev',) ) 
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failIf(hasattr(self.folder, 'dev'))
        self.failUnless(hasattr(self.folder.subfolder, 'dev'))
        self.failUnless(
            self.folder.subfolder.getPhysicalPath() == 
                dev.getPrimaryPath()[:-1])


    def testCutPasteRM2(self):
        """add contained relationship to cut/paste test"""
        dev = build(self.folder, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        cookie = self.folder.manage_cutObjects( ids=('dev',) ) 
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failIf(hasattr(self.folder, 'dev'))
        self.failUnless(hasattr(self.folder.subfolder, 'dev'))
        self.failUnless(
            self.folder.subfolder.getPhysicalPath() == 
                dev.getPrimaryPath()[:-1])
        self.failUnless(eth0.getPrimaryUrlPath().find(
                dev.getPrimaryUrlPath()) == 0)


    def testdelObjectRMwRel(self):
        """delete an RM that has many relationships on it"""
        dev = build(self.folder, Server, "dev")
        loc = build(self.folder, Location, "loc")
        jim = build(self.folder, Admin, "jim")
        group = build(self.folder, Group, "group")
        dev.admin.addRelation(jim)
        dev.groups.addRelation(group)
        dev.location.addRelation(loc)
        self.folder._delObject("dev")
        self.failIf(hasattr(self.folder, "dev"))


    def testCutPasteRMwRel(self):
        """cut and paste with relationships make sure they persist and
        that their keys are updated properly"""
        dev = build(self.folder, Server, "dev")
        loc = build(self.folder, Location, "loc")
        jim = build(self.folder, Admin, "jim")
        group = build(self.folder, Group, "group")
        dev.admin.addRelation(jim)
        dev.groups.addRelation(group)
        dev.location.addRelation(loc)
        cookie = self.folder.manage_cutObjects( ids=('dev',) ) 
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failIf(hasattr(self.folder, 'dev'))
        self.failUnless(hasattr(self.folder.subfolder, 'dev'))
        self.failUnless(dev in group.devices())
        self.failUnless(dev.admin() == jim)
        self.failUnless(dev.location() == loc)
        self.failUnless(hasattr(loc.devices, dev.getPrimaryId()))
        self.failUnless(hasattr(group.devices, dev.getPrimaryId()))


    def testCopyPasteRMPP(self):
        """test that primary path gets set correctly after copy and paste 
        where id doesn't change"""
        dev = build(self.folder, Device, "dev")
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.folder.subfolder, "dev"))
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(self.folder.subfolder.getPhysicalPath() == 
            copy.getPrimaryPath()[:-1])


    def testCopyPasteProperties(self):
        """test that Properties are copied correctly"""
        dev = build(self.folder, Device, "dev")
        dev.pingStatus = 3
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.folder.copy_of_dev, 'pingStatus'))
        copy = self.folder._getOb("copy_of_dev")
        self.failUnless(dev.pingStatus == copy.pingStatus)



def test_suite():
    return unittest.makeSuite(ToOneRel, 'to one rel tests')

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
