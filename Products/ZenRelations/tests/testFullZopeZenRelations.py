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


    def testCutPasteRM(self):
        """test cut and past of a RM make sure primarypath is set properly"""
        dev = build(self.folder, Device, "dev")
        cookie = self.folder.manage_cutObjects( ids=('dev',) ) 
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failIf(self.folder._getOb('dev', False))
        self.failUnless(self.folder.subfolder._getOb('dev'))
        self.failUnless(self.folder.subfolder.getPhysicalPath() == 
                        dev.getPrimaryPath()[:-1])


    def testCutPasteRM2(self):
        """add contained relationship to cut/paste test"""
        dev = build(self.folder, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        cookie = self.folder.manage_cutObjects( ids=('dev',) ) 
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failIf(self.folder._getOb('dev', False))
        self.failUnless(self.folder.subfolder._getOb('dev'))
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
        self.failIf(self.folder._getOb('dev', False))


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
        self.failIf(self.folder._getOb('dev', False))
        self.failUnless(self.folder.subfolder._getOb('dev'))
        self.failUnless(dev in group.devices())
        self.failUnless(dev.admin() == jim)
        self.failUnless(dev.location() == loc)
        self.failUnless(loc.devices.hasobject(dev))
        self.failUnless(group.devices.hasobject(dev))


    def testCopyPasteRMPP(self):
        """test that primary path gets set correctly after copy and paste"""
        dev = build(self.folder, Device, "dev")
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        self.failUnless(self.folder.subfolder._getOb('dev'))
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(self.folder.subfolder.getPhysicalPath() == 
            copy.getPrimaryPath()[:-1])


    def testCopyPasteRMSamePath(self):
        """Copy/Paste RM in same folder as original"""
        dev = build(self.folder, Device, "dev")
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(self.folder._getOb('dev'))
        self.failUnless(self.folder._getOb('copy_of_dev'))


    def testCopyPasteProperties(self):
        """test that Properties are copied correctly"""
        dev = build(self.folder, Device, "dev")
        dev.pingStatus = 3
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(self.folder.copy_of_dev._getOb('pingStatus'))
        copy = self.folder._getOb("copy_of_dev")
        self.failUnless(dev.pingStatus == copy.pingStatus)
        self.failUnless(dev.pingStatus == 3)
        

    def testCopyPasteRMOneToOne(self):
        """Copy/paste to check RM with OneToOne relationship"""
        dev = build(self.folder, Server, "dev")
        jim = build(self.folder, Admin, "jim")
        dev.admin.addRelation(jim)
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(dev.admin() == jim)
        self.failUnless(copy.admin() == None)


    def testCopyPasteRMOneToManyCont(self):
        """Copy/paste to check RM with OneToManyCont subobject"""
        dev = build(self.folder, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(self.folder.subfolder.getPhysicalPath() == 
                        copy.getPrimaryPath()[:-1])
        ceth0 = copy.interfaces()[0]
        self.failUnless(
            ceth0.getPrimaryId().find(copy.getPrimaryId()) == 0)
        self.failUnless(ceth0.device() == copy)

                 
    def testCopyPasteRMOneToMany(self):
        """Copy/paste to check RM with OneToMany relationship"""
        dev = build(self.folder, Device, "dev")
        anna = build(self.folder, Location, "anna")
        dev.location.addRelation(anna)
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(copy.location() == anna)
        self.failUnless(dev.location() == anna)
        self.failUnless(len(anna.devices()) == 2)


    def testCopyPasteRMManyToMany(self):
        """Copy/paste to check RM with ManyToMany relationship"""
        dev = build(self.folder, Device, "dev")
        group = build(self.folder, Group, "group")
        dev.groups.addRelation(group)
        cookie = self.folder.manage_copyObjects(ids=('dev',))
        self.folder.subfolder.manage_pasteObjects( cookie )
        copy = self.folder.subfolder._getOb("dev")
        self.failUnless(group in copy.groups())
        self.failUnless(group in dev.groups())
        self.failUnless(dev in group.devices())
        self.failUnless(copy in group.devices())


    def testRenameRMOneToOne(self):
        """Renameing RM that has a OneToOne relationship"""
        dev = build(self.folder, Server, "dev")
        jim = build(self.folder, Admin, "jim")
        dev.admin.addRelation(jim)
        self.folder.manage_renameObject("dev", "newdev")
        self.failUnless(self.folder._getOb("newdev"))
        self.failUnless(dev.admin.hasobject(jim))
        self.failUnless(jim.server.hasobject(dev))


    def testCopyPasteRMOneToManyCont(self):
        """Copy/paste to check RM with OneToManyCont subobject"""
        dev = build(self.folder, Device, "dev")
        eth0 = create(dev.interfaces, IpInterface, "eth0")
        self.folder.manage_renameObject("dev", "newdev")
        self.failUnless(self.folder._getOb("newdev"))
        self.failUnless(self.folder.getPhysicalPath() == 
                        dev.getPrimaryPath()[:-1])
        self.failUnless(dev.getPrimaryPath() == 
                        eth0.getPrimaryPath()[:-2])
        self.failUnless(eth0.device() == dev)


    def testRenameOneToMany(self):
        """Renaming RM that has a OneToMany relationship"""
        dev = build(self.folder, Device, "dev")
        anna = build(self.folder, Location, "anna")
        dev.location.addRelation(anna)
        self.failUnless(dev.location() == anna)
        self.folder.manage_renameObject("dev", "newdev")
        self.failUnless(self.folder._getOb("newdev"))
        self.failUnless(anna.devices.hasobject(dev))
        self.failUnless(dev.location() == anna)


    def testCopyPasteRMManyToMany(self):
        """Copy/paste to check RM with ManyToMany relationship"""
        dev = build(self.folder, Device, "dev")
        group = build(self.folder, Group, "group")
        dev.groups.addRelation(group)
        self.folder.manage_renameObject("dev", "newdev")
        self.failUnless(self.folder._getOb("newdev"))
        self.failUnless(group.devices.hasobject(dev))
        self.failUnless(dev.groups.hasobject(group))


def test_suite():
    return unittest.makeSuite(ToOneRel, 'to one rel tests')

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
