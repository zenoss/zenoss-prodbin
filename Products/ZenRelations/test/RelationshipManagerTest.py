#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToOneRelationshipTest

Tests for ToOneRelationship

$Id: RelationshipManagerTest.py,v 1.14 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

import pdb
import unittest

from Acquisition import aq_base

from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from SchemaManagerSetup import *
from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.RelationshipManager import manage_addRelationshipManager
from Products.ZenRelations.ToManyRelationship import manage_addToManyRelationship
from Products.ZenRelations.ToManyRelationship import manage_addToManyRelationship

from Products.ZenRelations.Exceptions import *


class RelationshipManagerTest(RelationshipManagerBaseTest, SchemaManagerSetup):
    
    def setUp(self):
        RelationshipManagerBaseTest.setUp(self)
        SchemaManagerSetup.setUp(self)
        self.app.mySchemaManager.addRelSchema(self.rsoto)
        self.app.mySchemaManager.addRelSchema(self.rsotm)
        self.app.mySchemaManager.addRelSchema(self.rsmtm)
        self.setUpSecurity()


    def tearDown(self):
        RelationshipManagerBaseTest.tearDown(self)
        SchemaManagerSetup.tearDown(self)
        self.tearDownSecurity()

    def testCascadeDeleteToOne(self):
        """test deleteing an object which has cascading delete on to one"""
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1).obj == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2).obj == self.app.ic1)
        self.app._delObject(self.app.ic1.id)
        self.failIf(filter(lambda o, n=self.ic1: n == aq_base(o), self.app.objectValues()))
        self.failIf(filter(lambda o, n=self.imt: n == aq_base(o), self.app.objectValues()))


    def testCascadeDeleteToMany(self):
        """test deleteing an object which has cascading delete on to Many"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.app._delObject(self.app.ic1.id)
        self.failIf(filter(lambda o, n=self.ic1: n == aq_base(o), self.app.objectValues()))
        self.failIf(filter(lambda o, n=self.ic3: n == aq_base(o), self.app.objectValues()))
   

    def testCascadeDeleteToMany2(self):
        """test deleteing an object which has cascading delete on to Many"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic1, self.mtm1)())
        self.app._delObject(self.app.ic1.id)
        self.failIf(filter(lambda o, n=self.ic1: n == aq_base(o), self.app.objectValues()))
        self.failIf(filter(lambda o, n=self.ic3: n == aq_base(o), self.app.objectValues()))
        self.failIf(filter(lambda o, n=self.ic32: n == aq_base(o), self.app.objectValues()))

    def testAddingNonRMtoRM(self):
        """test adding a non RM to an RM"""
        manage_addFolder(self.app.ic1, 'myfolder')
        self.failUnless(hasattr(self.app.ic1, 'myfolder'))


    def testAddingRMIntoRel(self):
        """test adding an RM in to a to many relationship check primaryPath"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        rel = getattr(self.app.ic1, self.mtm1)
        id = rel._setObject('ic33', self.ic33)
        self.failUnless(hasattr(rel, id))
        rpp = rel()[0].getPrimaryUrlPath()
        self.failUnless(rpp.find(self.app.ic1.getPrimaryUrlPath()) == 0)


    def testCutPasteRM(self):
        """test cut and past of a RM make sure primarypath is set and that rels work"""
        cookie = self.app.manage_cutObjects( ids=('imt',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.failIf(hasattr(self.app, 'imt'))
        self.failUnless(hasattr(self.app.folder, 'imt'))
        self.failUnless(
            self.app.folder.getPhysicalPath() == self.imt.getPrimaryPath()[:-1])


    def testCutPasteRM2(self):
        """add recursion to cut/paste test"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        rel = getattr(self.app.ic1, self.mtm1)
        rel._setObject('ic33', self.ic33)
        cookie = self.app.manage_cutObjects( ids=('ic1',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.failIf(hasattr(self.app, 'ic1'))
        self.failUnless(hasattr(self.app.folder, 'ic1'))
        self.failUnless(
            self.app.folder.getPhysicalPath() == self.ic1.getPrimaryPath()[:-1])
        self.failUnless(self.ic33.getPrimaryUrlPath().find(
                    self.ic1.getPrimaryUrlPath()) == 0)

    def testCutPasteRMwRel(self):
        """test cut and paste and check that relationships still are correct"""
        self.app.ic1.addRelation(self.oto1, self.app.imt) # add one to one
        self.app.ic1.addRelation(self.otm1, self.app.imt) # add one to many
        self.app.imt.addRelation(self.otm2, self.app.ic12)
        self.app.ic1.addRelation(self.mtm1, self.app.ic3) # add many to many
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)# next in many to many
        cookie = self.app.manage_cutObjects(ids = ('ic1',)) # get cookie
        self.folder.manage_pasteObjects(cookie) # paste in folder
        self.failUnless(self.folder.ic1.oto1() == self.app.imt)
        self.failUnless(self.app.imt.oto2() == self.folder.ic1)
        self.failUnless(self.app.imt.otm2() == [self.folder.ic1, self.app.ic12])
        self.failUnless(self.folder.ic1.otm1() == self.app.imt)
        self.failUnless(self.app.ic12.otm1() == self.app.imt)
        self.failUnless(self.folder.ic1 in self.app.ic3.mtm2())
        self.failUnless(self.folder.ic1 in self.app.ic32.mtm2())
            

    #def testCopyPasteRMPP(self):
    #    """test that primary path gets set correctly after copy and paste where id doesn't change"""
    #    cookie = self.app.manage_copyObjects(ids=('ic1',))
    #    self.app.folder.manage_pasteObjects( cookie )
    #    self.failUnless(self.app.folder.ic1.getPhysicalPath() == self.app.folder.ic1.getPrimaryPath())
   
    def testCopyPasteAttributes(self):
        """test that attributes are copied correctly"""
        self.app.folder.fc3.pingStatus = 3
        cookie = self.app.folder.manage_copyObjects(ids=('fc3',))
        self.app.folder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.app.folder.copy_of_fc3, 'pingStatus'))
        self.failUnless(
            self.app.folder.fc3.pingStatus == 
                self.app.folder.copy_of_fc3.pingStatus)

    
    def testCopyPasteRMPP(self):
        """test that primary path gets set correctly after copy and paste where id does change"""
        cookie = self.app.folder.manage_copyObjects(ids=('fc3',))
        self.app.folder.manage_pasteObjects( cookie )
        self.failUnless(self.app.folder.copy_of_fc3.getPhysicalPath() == 
                            self.app.folder.copy_of_fc3.getPrimaryPath())

    def testCopyPasteNoOrigChange(self):
        """test to make sure the original object didn't change"""
        self.app.imt.testatt = 3
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        id = rel._setObject('ic33', self.ic33)
        get_transaction().commit() #commit so that copy works
        cookie = self.app.manage_copyObjects( ids=('imt',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.app.imt, 'otm2'))
        self.failUnless(hasattr(self.app.imt.otm2, id))
        self.failUnless(self.app.imt.testatt == 3)


    def testCopyPasteRMPP2(self):
        """add recursion to copy/paste test and check that primary paths are correct with otm containment"""
        
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        rel._setObject('ic33', self.ic33)
        get_transaction().commit() #commit so that copy works
        cookie = self.app.manage_copyObjects( ids=('imt',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.app.folder, 'copy_of_imt'))
        cimt = self.app.folder.copy_of_imt
        self.failUnless(
            self.app.folder.getPhysicalPath() == cimt.getPrimaryPath()[:-1])
        cic33 = cimt._getOb(self.otm2)()[0]
        self.failUnless(
            cic33.getPrimaryUrlPath().find(cimt.getPrimaryUrlPath()) == 0)


    def testCopyPasteRMPP3(self):
        """add recursion to copy/paste test and check that primary paths are correct"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        rel = getattr(self.app.ic1, self.mtm1)
        rel._setObject('ic33', self.ic33)
        get_transaction().commit() #commit so that copy works
        cookie = self.app.manage_copyObjects( ids=('ic1',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(hasattr(self.app.folder, 'ic1'))
        cic1 = self.app.folder.copy_of_ic1
        self.failUnless(self.app.folder.getPhysicalPath() 
                                == cic1.getPrimaryPath()[:-1])
        cic33 = cic1._getOb(self.mtm1)()[0]
        self.failUnless(cic33.getPrimaryUrlPath().find(
            cic1.getPrimaryUrlPath()) == 0)


    def testCopyPasteRMOTO(self):
        """test copy and paste of an rm and check one to one rel"""
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        get_transaction().commit()
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)
        self.failUnless(
            getattr(self.app.folder.copy_of_ic1, self.oto1)() == None)


    def testCopyPasteRMOTM(self):
        """test copy and paste of an rm on many side of one to many"""
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        get_transaction().commit()
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.folder.manage_pasteObjects( cookie )
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2)())
        self.failUnless(
            self.app.folder.copy_of_ic1 in getattr(self.app.imt, self.otm2)())
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(
            getattr(self.app.folder.copy_of_ic1, self.otm1)() == self.app.imt)
   

    def testCopyPasteRMOTM2(self):
        """test copy and paste of an rm on one side of one to many"""
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        get_transaction().commit()
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.folder.manage_pasteObjects(cookie)
        self.failUnless(self.app.ic1.otm1() == \
            self.app.imt)
        self.failUnless(self.folder.copy_of_ic1 in \
            self.app.imt.otm2())
        self.failUnless(self.app.ic1 in \
            self.app.imt.otm2())
        self.failUnless(self.folder.copy_of_ic1.otm1() == \
            self.app.imt)

    def testCopyPasteRMMTM(self):
        """test copy and paste of an rm on many to many"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        get_transaction().commit()
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.folder.manage_pasteObjects(cookie)
        self.failUnless(self.app.ic1 in self.app.ic3.mtm2())
        self.failUnless(self.app.ic3 in self.app.ic1.mtm1())
        self.failUnless(self.app.ic3 in self.folder.copy_of_ic1.mtm1())
        self.failUnless(self.folder.copy_of_ic1 in self.app.ic3.mtm2())
            
    
    def testRenameRM(self):
        """test renaming an rm to make sure the remote ids get updated"""
        cookie = self.app.manage_cutObjects( ids=('ic1',) ) 
        self.folder.manage_pasteObjects( cookie )
        self.app.folder.ic1.addRelation(self.oto1, self.app.imt)
        self.app.folder.ic1.addRelation(self.otm1, self.app.imt)
        self.app.folder.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.folder.ic1.addRelation(self.mtm1, self.app.ic32)
        self.app.folder.manage_renameObject(id='ic1', new_id='nic1')
        self.failUnless(getattr(self.app.imt, self.oto2)() 
                                    == self.app.folder.nic1)
        self.failUnless(getattr(self.app.imt, self.oto2).title == 'nic1')
        nic1 = self.app.folder.nic1
        self.failUnless(self.app.imt.otm2.hasobject(nic1))
        self.failUnless(self.app.ic3.mtm2.hasobject(nic1))
        self.failUnless(self.app.ic32.mtm2.hasobject(nic1))


if __name__ == "__main__":
    unittest.main()
