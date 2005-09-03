#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

from RMBaseTest import RMBaseTest
from TestSchema import *

from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship
from Products.ZenRelations.Exceptions import *

class ToOneRelationshipTest(RMBaseTest):

    def testmanage_addToOneRelationship(self):
        """Test adding a to one relationship"""
        dev = self.create(self.app, Server, "dev")
        manage_addToOneRelationship(dev, "admin")
        self.failUnless(hasattr(dev, "admin"))


    def testmanage_addToOneRelationshipBad(self):
        """test adding to many to an invalid container""" 
        self.failUnlessRaises(InvalidContainer, 
            manage_addToOneRelationship, self.app.folder, "admin")


    def testmanage_addToOneRelationshipSchemaBad(self):
        """add a relationship with invalid schema"""
        dev = self.create(self.app, Server, "dev")
        self.failUnlessRaises(SchemaError,
                    manage_addToOneRelationship, dev, 'lkjlkjlkjlkj')


    def testaddRelationOneToOne(self):
        """Test addRelation in a one to one"""
        dev = self.create(self.app, Server, "dev")
        jim = self.create(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)


    def testaddRelationOneToOne2(self):
        """Test addRelation in where both sides of realtionship exist"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)


    def testaddRelationOneToOne3(self):
        """Test addRelation on the ToOneRelationship itself"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.admin.addRelation(jim)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)



    def testaddRelationOneToOneNone(self):
        """Test addRelation in a one to one with None"""
        dev = self.build(self.app, Server, "dev")
        self.failUnlessRaises(RelationshipManagerError, dev.addRelation, 
                              "admin", None)


    def testaddRelationOneToOneOverwrite(self):
        """Test addRelation over write of relationship"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        nate = self.build(self.app, Admin, "nate")
        dev.addRelation("admin", jim)
        dev.addRelation("admin", nate)
        self.failUnless(dev.admin() == nate)
        self.failUnless(nate.server() == dev)
        self.failUnless(jim.server() == None)


    def testDeletingRelationship(self):
        """Test deleting the relationship object itself, 
        make sure the link is removed"""
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        dev._delObject("admin")
        self.failIf(hasattr(dev, "admin"))
        self.failUnless(jim.server() == None)


    def testLinkObjectsUI(self):
        """Test linking objects using the UI code """
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        cookie = self.app.manage_copyObjects(ids=('jim',))
        self.failUnless(cookie)
        self.app.dev.manage_linkObjects(ids=("admin",), cb_copy_data=cookie)
        self.failUnless(jim.server() == dev)
        self.failUnless(dev.admin() == jim)


    def testUnLinkObjectsUI(self):
        """Test unlinking objects using the UI code """
        dev = self.build(self.app, Server, "dev")
        jim = self.build(self.app, Admin, "jim")
        dev.addRelation("admin", jim)
        self.app.dev.manage_unlinkObjects(ids=("admin",))
        self.failUnless(dev.admin() == None)
        self.failUnless(jim.server() == None)


#=============================================================================
#=============================================================================

from Products.ZenRelations.ToManyRelationship \
    import manage_addToManyRelationship
 
class ToManyRelationshipTest(RMBaseTest):


    def testmanage_addToManyRelationship(self):
        """Test adding a to one relationship"""
        dev = self.create(self.app, Device, "dev")
        manage_addToManyRelationship(dev, "interfaces")
        self.failUnless(hasattr(dev, "interfaces"))


    def testmanage_addToManyRelationshipBad(self):
        """test adding to many to an invalid container""" 
        self.failUnlessRaises(InvalidContainer, 
            manage_addToManyRelationship, self.app.folder, "interfaces")


    def testmanage_addToManyRelationshipSchemaBad(self):
        """add a relationship with invalid schema"""
        dev = self.create(self.app, Device, "dev")
        self.failUnlessRaises(SchemaError,
                    manage_addToManyRelationship, dev, 'lkjlkjlkjlkj')


    def testFindObjectsById(self):
        """Test removeRelation on a to many object itself """
        dev = self.build(self.app, Device, "dev")
        self.create(dev.interfaces, IpInterface, "eth0")
        self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces.findObjectsById("eth0"))==1)


    def testaddRelationOneToMany(self):
        """Test froming a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        loc = self.create(self.app, Location, "loc")
        loc.addRelation("devices", dev)
        self.failUnless(dev in loc.devices())
        self.failUnless(dev.location() == loc)


    def testaddRelationOneToMany2(self):
        """Test froming a one to many relationship reverse"""
        dev = self.create(self.app, Device, "dev")
        loc = self.create(self.app, Location, "loc")
        dev.addRelation("location", loc)
        self.failUnless(dev in loc.devices())
        self.failUnless(dev.location() == loc)
   

    def testaddRelationOneToManyOverwrite(self):
        """Test setting the one side of one to many twice with same object"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        riva = self.create(self.app, Location, "riva")
        dev.addRelation("location", anna)
        dev.addRelation("location", riva)
        self.failUnless(dev in riva.devices())
        self.failUnless(len(anna.devices())==0)
        self.failUnless(dev.location() == riva)


    def testaddRelationToManyNone(self):
        """Test adding None to a to many relationship"""
        dev = self.create(self.app, Device, "dev")
        self.failUnlessRaises(RelationshipManagerError, 
                dev.addRelation, "location", None)


    def testaddRelationOnToMany(self):
        """Test addRelation on a to many object itself """
        dev = self.create(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)


    def testremoveRelationOneToMany(self):
        """Test removing from a to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        self.failUnless(dev.location() == anna)
        anna.removeRelation("devices", dev)
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())


    def testremoveRelationOneToMany2(self):
        """Test removing from a to many relationship with two objects"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        anna.addRelation("devices", dev2)
        self.failUnless(dev.location() == anna)
        self.failUnless(dev2.location() == anna)
        anna.removeRelation("devices", dev)
        self.failUnless(dev.location() == None)
        self.failIf(dev in anna.devices())
        self.failUnless(dev2 in anna.devices())


    def testremoveRelationOneToMany3(self):
        """Test removing from to one side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        self.failUnless(dev.location() == anna)
        dev.location.removeRelation(anna)
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())
 

    def testremoveRelationOneToMany4(self):
        """Test removing all from to one side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        dev2 = self.create(self.app, Device, "dev2")
        anna = self.create(self.app, Location, "anna")
        anna.addRelation("devices", dev)
        anna.addRelation("devices", dev2)
        self.failUnless(len(anna.devices()) == 2)
        anna.removeRelation("devices")
        self.failUnless(len(anna.devices()) == 0)
        self.failUnless(dev.location() == None)
        self.failUnless(dev2.location() == None)


    def testremoveRelationOnToMany(self):
        """Test removeRelation on a to many object itself """
        dev = self.create(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        anna.devices.addRelation(dev)
        self.failUnless(dev.location() == anna)
        anna.devices.removeRelation()
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())


    def testLinkToMany(self):
        """link on to one side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        cookie = self.app.manage_copyObjects(ids=('anna',))
        self.failUnless(cookie)
        self.app.dev.manage_linkObjects(ids=("location",), cb_copy_data=cookie)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)


    def testLinkToMany2(self):
        """link on to many side of a one to many relationship"""
        dev = self.create(self.app, Device, "dev")
        anna = self.create(self.app, Location, "anna")
        cookie = self.app.manage_copyObjects(ids=('dev',))
        self.failUnless(cookie)
        self.app.anna.manage_linkObjects(ids=("devices",), cb_copy_data=cookie)
        self.failUnless(dev in anna.devices())
        self.failUnless(dev.location() == anna)


    def testUnLinkToMany(self):
        """Test unlinking to one side of one to many using the UI code """
        dev = self.build(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        dev.location.addRelation(anna)
        self.failUnless(dev.location() == anna)
        self.app.dev.manage_unlinkObjects(ids=("location",))
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())


    def testUnLinkToMany2(self):
        """Test unlinking to many side of one to many using the UI code """
        dev = self.build(self.app, Device, "dev")
        anna = self.build(self.app, Location, "anna")
        dev.location.addRelation(anna)
        self.failUnless(dev.location() == anna)
        self.app.anna.manage_unlinkObjects(ids=("devices",))
        self.failIf(dev.location() == anna)
        self.failIf(dev in anna.devices())


# FIXME: zope permissions or something prevent rename
#           need to investigate more to understand
#           
# Traceback (most recent call last):
#   File "testZenRelations.py", line 312, in testRenameToMany
#     self.app.manage_renameObject("dev", "newdev")
#   File "/Users/edahl/Zope-2.8.1-final/lib/python/OFS/CopySupport.py", line 269, in manage_renameObject
#     self._verifyObjectPaste(ob)
#   File "/Users/edahl/Zope-2.8.1-final/lib/python/OFS/CopySupport.py", line 428, in _verifyObjectPaste
#     action  = 'manage_main')
#     def testRenameToMany(self):
#         """test renaming an object that has a tomany relationship"""
#         dev = self.build(self.app, Device, "dev")
#         anna = self.build(self.app, Location, "anna")
#         dev.location.addRelation(anna)
#         self.failUnless(dev.location() == anna)
#         self.app.manage_renameObject("dev", "newdev")
#         self.failUnless(hasattr(self.app, "newdev"))
#         self.failUnless(hasattr(anna.devices, "newdev"))
#         self.failIf(hasattr(anna.devices, "dev"))


    def testaddRelationOneToManyCont(self):
        """Test froming a one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth in dev.interfaces())
        self.failUnless(eth.device() == dev)


    def testremoveRelationOneToManyCont(self):
        """Test removing a one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        self.failUnless(eth.device() == dev)
        dev.removeRelation("interfaces", eth)
        self.failUnless(len(dev.interfaces()) == 0)


    def testremoveRelationOneToManyCont2(self):
        """Test removing all objects from one to many contained relationship"""
        dev = self.build(self.app, Device, "dev")
        eth = self.create(dev.interfaces, IpInterface, "eth0")
        eth1 = self.create(dev.interfaces, IpInterface, "eth1")
        self.failUnless(len(dev.interfaces()) == 2)
        dev.removeRelation("interfaces")
        self.failUnless(len(dev.interfaces()) == 0)
        


    def testaddRelationManyToMany(self):
        """Test froming a many to many relationship"""


def test_suite():
    return unittest.makeSuite(ToOneRel, 'to one rel tests')

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
