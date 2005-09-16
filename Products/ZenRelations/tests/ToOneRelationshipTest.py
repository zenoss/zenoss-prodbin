#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToOneRelationshipTest

Tests for ToOneRelationship

$Id: ToOneRelationshipTest.py,v 1.7 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

import Globals

import unittest
from Acquisition import aq_base
from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from SchemaManagerSetup import *

from Products.ZenRelations.SchemaManager import manage_addSchemaManager
from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship

from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.Exceptions import *

class ToOneRelationshipTest(RelationshipManagerBaseTest, SchemaManagerSetup):


    def setUp(self):
        RelationshipManagerBaseTest.setUp(self)
        SchemaManagerSetup.setUp(self)
        self.app.ZenSchemaManager.addRelSchema(self.rsoto)
        self.app.ZenSchemaManager.addRelSchema(self.rsotm)
        self.app.ZenSchemaManager.addRelSchema(self.rsmtm)
        self.setUpSecurity()


    def tearDown(self):
        RelationshipManagerBaseTest.tearDown(self)
        SchemaManagerSetup.tearDown(self)
        self.tearDownSecurity()


    def testmanage_addToOneRelationship(self):
        """Test adding a to one relationship"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.failUnless(hasattr(self.ic1, self.oto1))


    def testmanage_addToOneRelationshipBad(self):
        """test adding to many to an invalid container""" 
        self.failUnlessRaises(InvalidContainer, 
                    manage_addToOneRelationship, self.app.folder, self.oto1)


    def testmanage_addToOneRelationshipSchemaBad(self):
        """add a relationship with invalid schema"""
        self.failUnlessRaises(SchemaError,
                    manage_addToOneRelationship, self.app.imt, 'lkjlkjlkjlkj')


    def testaddRelationOneToOne(self):
        """Test addRelation in a one to one"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)


    def testaddRelationOneToOne2(self):
        """Test addRelation in where both sides of realtionship exist"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        manage_addToOneRelationship(self.app.imt, self.oto2)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)

    
    def testaddRelationOneToOneNoRel(self):
        """Test addRelation when there no relationship has been made on the object"""
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)


    def testaddRelationOneToOneNone(self):
        """Test addRelation in a one to one with None"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.failUnlessRaises(RelationshipManagerError, 
                    self.app.ic1.addRelation, self.oto1, None)


    def testremoveRelationOneToOne(self):
        """Test removeRelation in a one to one"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.app.ic1.removeRelation(self.oto1)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == None)
        self.failUnless(getattr(self.app.imt, self.oto2)() == None)


    def testaddRelationOneToOneOverwrite(self):
        """Test addRelation over write of relationship"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.app.ic1.addRelation(self.oto1, self.app.imt2)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt2)
        self.failUnless(getattr(self.app.imt2, self.oto2)() == self.app.ic1)
        self.failUnless(getattr(self.app.imt, self.oto2)() == None)


    def testaddRelationOneToOneOverwrite2(self):
        """Test addRelation over write of relationship from other side"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.app.imt.addRelation(self.oto2, self.app.ic12)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic12)
        self.failUnless(getattr(self.app.ic12, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == None)


    def testDeletingRelationship(self):
        """Test deleting the relationship object itself, make sure the link is removed"""
        manage_addToOneRelationship(self.app.ic1, self.oto1)
        self.app.ic1.addRelation(self.oto1, self.app.imt)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.app.ic1._delObject(self.oto1)
        self.failIf(hasattr(self.app.ic1, self.oto1))
        self.failUnless(getattr(self.app.imt, self.oto2)() == None)


    def testLinkObjectsUI(self):
        """Test linking objects using the UI code """
        cookie = self.app.manage_copyObjects(ids=('imt',))
        self.failUnless(cookie)
        self.app.ic1.manage_linkObjects(ids=(self.oto1,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)
  

    def testUnLinkObjectsUI(self):
        """Test unlinking objects using the UI code """
        cookie = self.app.manage_copyObjects(ids=('imt',))
        self.failUnless(cookie)
        self.app.ic1.manage_linkObjects(ids=(self.oto1,), cb_copy_data=cookie)
        self.failUnless(getattr(self.app.ic1, self.oto1)() == self.app.imt)
        self.failUnless(getattr(self.app.imt, self.oto2)() == self.app.ic1)
        self.app.ic1.manage_unlinkObjects(ids=(self.oto1,))
        self.failUnless(getattr(self.app.ic1, self.oto1)() == None)
        self.failUnless(getattr(self.app.imt, self.oto2)() == None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( ToOneRelationshipTest ) )
    return suite


if __name__ == "__main__":
    unittest.main()
