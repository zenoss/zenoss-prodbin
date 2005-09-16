#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SchemaManagerTest

Tests for SchemaManager

$Id: SchemaManagerTest.py,v 1.6 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import unittest
from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from SchemaManagerSetup import SchemaManagerSetup, MT_TYPE

from Products.ZenRelations.SchemaManager import manage_addSchemaManager
from Products.ZenRelations.RelationshipSchema import RelationshipSchema, manage_addRelationshipSchema

from Products.ZenRelations.RelTypes import *
from Products.ZenRelations.Exceptions import *


class SchemaManagerTest(RelationshipManagerBaseTest, SchemaManagerSetup):
 
    def setUp(self):
        RelationshipManagerBaseTest.setUp(self)
        SchemaManagerSetup.setUp(self)
        self.sm = self.app.ZenSchemaManager


    def tearDown(self):
        RelationshipManagerBaseTest.tearDown(self)
        del self.sm 


    def testmanage_addRelationshipSchema(self):
        """test the RelationshipSchema Factory"""
        manage_addRelationshipSchema(self.sm, 
                                        self.c1, self.oto1, TO_ONE,
                                        self.mt, self.oto2, TO_ONE)
        self.failUnless(len(self.sm.objectValues()) == 1)
        rs = self.sm.objectValues()[0]
        self.failUnless(self.sm._getOb(rs.id).classOne() == self.c1)
    
    def test_setObject(self):
        """test adding a relationship manager through the management interface"""
        self.sm._setObject(self.rsoto.id, self.rsoto)
        self.failUnless(len(self.sm.objectValues()) == 1)
        rs = self.sm.objectValues()[0]
        self.failUnless(self.sm._getOb(rs.id) == self.rsoto)
        
    def testAddRelSchema(self):
        """test adding a relation"""
        self.sm.addRelSchema(self.rsoto)
        self.failUnless(self.sm._schema.has_key(self.c1))
        self.failUnless(self.sm._schema[self.c1].has_key(self.oto1))
        self.failUnless(self.sm._schema.has_key(self.mt))
        self.failUnless(self.sm._schema[self.mt].has_key(self.oto2))

    def testAddDuplicateSchema(self):
        """test adding duplicate schema objects """
        self.sm.addRelSchema(self.rsoto)
        self.failUnlessRaises(SchemaError, self.sm.addRelSchema, self.rsoto)


    def testRemoveRelSchema(self):
        """test removing relation from a class with only one"""
        self.sm.addRelSchema(self.rsoto)
        self.sm.removeRelSchema(self.rsoto)
        self.failIf(self.sm._schema.has_key(self.c1))
        self.failIf(self.sm._schema.has_key(self.mt))


    def testRemoveRelSchema2(self):
        """test removing relation from a class with more than one"""
        self.sm.addRelSchema(self.rsoto)
        self.sm.addRelSchema(self.rsotm)
        self.sm.removeRelSchema(self.rsoto)
        self.failUnless(self.sm._schema.has_key(self.c1))
        self.failIf(self.sm._schema[self.c1].has_key(self.oto1))
        self.failIf(self.sm._schema.has_key(self.mt))


    def testGetRelSchemaMeta_type(self):
        """test meta_type lookup"""
        self.sm.addRelSchema(self.rsoto)
        self.sm.addRelSchema(self.rsotm)
        self.sm.addRelSchema(self.rsmtm)
        rel = self.sm.getRelSchema(self.imt, self.otm2)
        self.failUnless(rel.relTwo() == self.otm2)
   

    def testGetRelSchemaClass(self):
        """test class lookup"""
        self.sm.addRelSchema(self.rsoto)
        self.sm.addRelSchema(self.rsotm)
        self.sm.addRelSchema(self.rsmtm)
        rel = self.sm.getRelSchema(self.ic1, self.oto1)
        self.failUnless(rel.relOne() == self.oto1)
        
    def testGetRelSchemaInherit(self):
        """test class lookup using inheritence"""
        self.sm.addRelSchema(self.rsoto)
        self.sm.addRelSchema(self.rsotm)
        self.sm.addRelSchema(self.rsmtm)
        rel = self.sm.getRelSchema(self.ic3, self.mtm2)
        self.failUnless(rel.relTwo() == self.mtm2)


if __name__ == "__main__":
    unittest.main()
