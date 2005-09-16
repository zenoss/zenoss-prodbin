#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipSchemaTest2

Tests for RelatinoshipSchema

$Id: RelationshipSchemaTest2.py,v 1.2 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
from RelationshipManagerBaseTest import RelationshipManagerBaseTest
from Products.ZenRelations.RelationshipSchema import manage_addRelationshipSchema
from Products.ZenRelations.SchemaManager import SchemaManager, manage_addSchemaManager
from Products.ZenRelations.RelTypes import *

class RelationshipSchemaTest2(RelationshipManagerBaseTest):
    
    classOne = "c1"
    relOne = "r1"
    classTwo = "c2"
    relTwo = "r2"
    relType = TO_MANY
    relTypeTwo = TO_ONE    
    
    def setUp(self):
        RelationshipManagerBaseTest.setUp(self)
        manage_addSchemaManager(self.app)
        self.sm = self.app.ZenSchemaManager
        manage_addRelationshipSchema(self.sm, 
                            self.classOne, self.relOne, self.relType,
                            self.classTwo, self.relTwo, self.relTypeTwo)
        self.rs = self.sm.objectValues()[0]

    def tearDown(self):
        RelationshipManagerBaseTest.tearDown(self)
        del self.sm
        del self.rs


    def testChangeClass(self):
        """Test changing class one attribute"""
        self.rs.classOne("asdf")
        self.failUnless(self.rs.classOne() == "asdf")
        self.failUnless(self.sm._schema.has_key("asdf"))
        self.failUnless(self.sm._schema["asdf"].has_key(self.relOne))


    def testChangeClass2(self):
        """Test changing class two attribute"""
        self.rs.classTwo("asdf")
        self.failUnless(self.rs.classTwo() == "asdf")
        self.failUnless(self.sm._schema.has_key("asdf"))
        self.failUnless(self.sm._schema["asdf"].has_key(self.relTwo))


    def testChangeRel(self):
        """Test changing rel one attribute"""
        self.rs.relOne("asdf")
        self.failUnless(self.rs.relOne() == "asdf")


    def testChangeRel2(self):
        """Test changing rel two attribute"""
        self.rs.relTwo("asdf")
        self.failUnless(self.rs.relTwo() == "asdf")

if __name__ == "__main__":
    unittest.main()
