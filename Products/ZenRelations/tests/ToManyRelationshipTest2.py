#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ToManyRelationshipTest2

Tests for ToManyRelationship using Many to Many relation

$Id: ToManyRelationshipTest2.py,v 1.8 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

import pdb
import unittest

from Acquisition import aq_base
from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from SchemaManagerSetup import *

from Products.ZenRelations.SchemaManager import manage_addSchemaManager
from Products.ZenRelations.ToOneRelationship import manage_addToOneRelationship
from Products.ZenRelations.ToManyRelationship import manage_addToManyRelationship

from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.Exceptions import *

class ToManyRelationshipTest2(RelationshipManagerBaseTest, SchemaManagerSetup):

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


    def testaddRelationManyToMany(self):
        """Test froming a many to many relationship"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())


    def testaddRelationManyToManyNoRel(self):
        """Test froming a many to many relationship with no relationships instantiated"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())


    def testaddRelationToManyNone(self):
        """Test adding None to a to many relationship"""
        self.failUnlessRaises(RelationshipManagerError, self.app.ic1.addRelation, self.mtm1, None)


    def testremoveRelationManyToMany(self):
        """Test removing from a to many relationship"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.app.ic1.removeRelation(self.mtm1, self.app.ic3)
        self.failIf(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failIf(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())


    def testremoveRelationManyToMany2(self):
        """Test removing from a to many relationship with two objects"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.app.ic12.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic1 in getattr(self.app.ic32, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic12, self.mtm1)())
        self.app.ic1.removeRelation(self.mtm1, self.app.ic3)
        self.failIf(self.app.ic3 in self.app.ic1.mtm1())
        self.failUnless(self.app.ic1 in getattr(self.app.ic32, self.mtm2)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic12, self.mtm1)())
        self.failUnless(self.app.ic12 in getattr(self.app.ic32, self.mtm2)())


    def testremoveRelationManyToMany4(self):
        """Test removing all from to one side of a one to many relationship"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.app.ic12.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic1 in getattr(self.app.ic32, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic12, self.mtm1)())
        self.app.ic1.removeRelation(self.mtm1)
        self.failIf(len(getattr(self.app.ic1, self.mtm1)()))

    # took this out now you can add dup it just makes sure its going
    # in the right collection (owned or related)
    #def testaddRelationDuplicate(self):
    #    """Test adding a duplicate to a to many 
    #        should throw RelationshipExistsError"""
    #    self.app.ic1.addRelation(self.mtm1, self.app.ic3)
    #    self.failUnlessRaises(RelationshipExistsError, 
    #            self.app.ic1.addRelation, self.mtm1, self.app.ic3)
       

    def testDeteteToManyRelationship(self):
        """Test deleteing the to many side of a one to many relationship"""
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.app.ic12.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failUnless(self.app.ic1 in getattr(self.app.ic32, self.mtm2)())
        self.failUnless(self.app.ic3 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic1, self.mtm1)())
        self.failUnless(self.app.ic32 in getattr(self.app.ic12, self.mtm1)())
        self.app.ic1._delObject(self.mtm1)
        self.failIf(self.app.ic1 in getattr(self.app.ic3, self.mtm2)())
        self.failIf(self.app.ic1 in getattr(self.app.ic32, self.mtm2)())


    def testObjectValuesManyToMany(self):
        """test that object values only returns contained objects not related objects"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        rel = getattr(self.app.ic1, self.mtm1)
        oid = rel._setObject('ic33', self.ic33)
        self.ic33 = rel._getOb(oid)
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(hasattr(rel, 'ic33'))
        self.failIf(self.app.ic3 in rel.objectValues())
        self.failIf(self.app.ic32 in rel.objectValues())

    def testObjectValuesAllManyToMany(self):
        """test that objectValuesAll returns ALL objects"""
        manage_addToManyRelationship(self.app.ic1, self.mtm1)
        rel = getattr(self.app.ic1, self.mtm1)
        oid = rel._setObject('ic33', self.ic33)
        self.ic33 = rel._getOb(oid)
        self.app.ic1.addRelation(self.mtm1, self.app.ic3)
        self.app.ic1.addRelation(self.mtm1, self.app.ic32)
        self.failUnless(self.ic33 in rel.objectValuesAll())
        self.failUnless(self.app.ic3 in rel.objectValuesAll())
        self.failUnless(self.app.ic32 in rel.objectValuesAll())

if __name__ == "__main__":
    unittest.main()
