#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToManyRelationshipTest

Tests for ToManyRelationship using One To Many relationship

$Id: ToManyRelationshipTest.py,v 1.12 2003/11/06 17:59:50 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

import unittest
from Acquisition import aq_base
from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from SchemaManagerSetup import *

from Products.ZenRelations.SchemaManager import manage_addSchemaManager
from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship
from Products.ZenRelations.ToManyRelationship import manage_addToManyRelationship

from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.Exceptions import *

class ToManyRelationshipTest(RelationshipManagerBaseTest, SchemaManagerSetup):

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


    def testmanage_addToManyRelationship(self):
        """Test adding a to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.failUnless(hasattr(self.imt, self.otm2))


    def testmanage_addToManyRelationshipBad(self):
        """test adding to many to an invalid container""" 
        self.failUnlessRaises("InvalidContainer", 
                    manage_addToManyRelationship, self.app.folder, self.otm2)


    def testmanage_addToManyRelationshipSchemaBad(self):
        """add a relationship with invalid schema"""
        self.failUnlessRaises(SchemaError,
                    manage_addToManyRelationship, self.app.imt, 'lkjlkjlkjlkj')


    def testFindObjectsById(self):
        """Test removeRelation on a to many object itself """
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        rel.addRelation(self.app.ic1)
        self.failUnless(len(rel.findObjectsById("ic1")) > 0)


    def testaddRelationOneToMany(self):
        """Test froming a one to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 
            in getattr(self.app.imt, self.otm2).objectValues())


    def testaddRelationOneToMany2(self):
        """Test froming a one to many relationship reverse"""
        manage_addToOneRelationship(self.app.ic1, self.otm1)
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 
            in getattr(self.app.imt, self.otm2).objectValues())

    
    def testaddRelationOneToManyOverwrite(self):
        """Test setting the one side of one to many twice with same object"""
        manage_addToOneRelationship(self.app.ic1, self.otm1)
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 
            in getattr(self.app.imt, self.otm2).objectValues())


    def testaddRelationOneToManyNoRel(self):
        """Test froming a one to many relationship with no 
            relationships instantiated"""
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 
            in getattr(self.app.imt, self.otm2).objectValues())


    def testaddRelationOneToMany2NoRel(self):
        """Test froming a one to many relationship with no 
            relationships instantiated reverse"""
        self.app.ic1.addRelation(self.otm1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 
            in getattr(self.app.imt, self.otm2).objectValues())

    def testaddRelationToManyNone(self):
        """Test adding None to a to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.failUnlessRaises(RelationshipManagerError, 
                self.app.imt.addRelation, self.otm2, None)


    def testaddRelationOnToMany(self):
        """Test addRelation on a to many object itself """
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        rel.addRelation(self.app.ic1)
        self.failUnless(self.app.ic1 in 
            getattr(self.app.imt, self.otm2).objectValues())



    def testremoveRelationOneToMany(self):
        """Test removing from a to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        self.app.imt.removeRelation(self.otm2, self.app.ic1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failIf(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())


    def testremoveRelationOneToMany2(self):
        """Test removing from a to many relationship with two objects"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.app.imt.addRelation(self.otm2, self.app.ic12)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        self.failUnless(self.app.ic12 in getattr(self.app.imt, self.otm2).objectValues())
        self.app.imt.removeRelation(self.otm2, self.app.ic12)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == None)
        self.failUnless(self.app.ic1 in 
                getattr(self.app.imt, self.otm2).objectValues())
        self.failIf(self.app.ic12 in 
                getattr(self.app.imt, self.otm2).objectValues())


    def testremoveRelationOneToMany3(self):
        """Test removing from to one side of a one to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in 
                getattr(self.app.imt, self.otm2).objectValues())
        self.app.ic1.removeRelation(self.otm1)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failIf(len(getattr(self.app.imt, self.otm2).objectValues()))
        self.failIf(self.app.ic1 in 
                getattr(self.app.imt, self.otm2).objectValues())


    def testremoveRelationOneToMany4(self):
        """Test removing all from to one side of a one to many relationship"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.app.imt.addRelation(self.otm2, self.app.ic12)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == self.app.imt)
        self.app.imt.removeRelation(self.otm2)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == None)
        self.failIf(len(getattr(self.app.imt, self.otm2).objectValues()))
        self.failIf(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        self.failIf(self.app.ic12 in getattr(self.app.imt, self.otm2).objectValues())


    def testremoveRelationOnToMany(self):
        """Test removeRelation on a to many object itself """
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        rel.addRelation(self.app.ic1)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        rel.removeRelation(self.app.ic1)
        self.failIf(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())


    def testremoveRelationOnToManyAlias(self):
        """Test removeRelation on a to many object itself where obj is alias"""
        manage_addToManyRelationship(self.app.imt, self.otm2)
        rel = getattr(self.app.imt, self.otm2)
        rel.addRelation(self.app.ic1)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        ra = getattr(rel, 'ic1')
        rel.removeRelation(ra)
        self.failIf(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())


    def testaddRelationOneToManyOverwrite(self):
        """Test overwrite of a one to many relationship"""
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.app.imt2.addRelation(self.otm2, self.app.ic1)
        self.failIf(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt2)
        self.failIf(self.app.ic1 in getattr(self.app.imt, self.otm2).objectValues())
        self.failUnless(self.app.ic1 in getattr(self.app.imt2, self.otm2).objectValues())
   
    # took this out now you can add dup it just makes sure its going
    # in the right collection (owned or related)
    #def testaddRelationDuplicate(self):
    #    """Test adding a duplicate to a to many 
    #    should throw RelationshipExistsError"""
    #    self.app.imt.addRelation(self.otm2, self.app.ic1)
    #    self.failUnlessRaises(RelationshipExistsError, 
    #        self.app.imt.addRelation, self.otm2, self.app.ic1)
       

    def testDeteteToManyRelationship(self):
        """Test deleteing the to many side of a one to many relationship"""
        self.app.imt.addRelation(self.otm2, self.app.ic1)
        self.app.imt.addRelation(self.otm2, self.app.ic12)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == self.app.imt)
        self.app.imt._delObject(self.otm2)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failUnless(getattr(self.app.ic12, self.otm1)() == None)


    def testLinkToMany(self):
        """link on to one side of a one to many relationship"""
        cookie = self.app.manage_copyObjects(ids=('imt',))
        self.failUnless(cookie)
        self.app.ic1.manage_linkObjects(ids=(self.otm1,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2)())


    def testLinkToMany2(self):
        """link on to many side of a one to many relationship"""
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.failUnless(cookie)
        self.app.imt.manage_linkObjects(ids=(self.otm2,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2)())


    def testUnLinkToMany(self):
        """Test unlinking to one side of one to many using the UI code """
        cookie = self.app.manage_copyObjects(ids=('imt',))
        self.failUnless(cookie)
        self.app.ic1.manage_linkObjects(ids=(self.otm1,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2)())
        self.app.ic1.manage_unlinkObjects(ids=(self.otm1,))
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failUnless(len(getattr(self.app.imt, self.otm2)()) == 0 )


    def testUnLinkToMany2(self):
        """Test unlinking to many side of one to many using the UI code """
        cookie = self.app.manage_copyObjects(ids=('ic1',))
        self.failUnless(cookie)
        self.app.imt.manage_linkObjects(ids=(self.otm2,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.otm1)() == self.app.imt)
        self.failUnless(self.app.ic1 in getattr(self.app.imt, self.otm2)())
        self.app.imt.manage_unlinkObjects(ids=(self.otm2,))
        self.failUnless(getattr(self.app.ic1, self.otm1)() == None)
        self.failUnless(len(getattr(self.app.imt, self.otm2)()) == 0 )

    def testRenameToMany(self):
        """test renaming an object that has a tomany relationship (doesn't work now)"""
        pass


if __name__ == "__main__":
    unittest.main()
