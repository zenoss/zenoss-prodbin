#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RelationshipSchemaTest

Tests for RelatinoshipSchema

$Id: RelationshipSchemaTest.py,v 1.5 2003/10/21 17:22:58 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

import unittest
from RelationshipManagerBaseTest import RelationshipManagerBaseTest

from Products.ZenRelations.RelationshipSchema import RelationshipSchema
from Products.ZenRelations.RelTypes import *

class RelationshipSchemaTest(RelationshipManagerBaseTest):
    
    classOne = "c1"
    relOne = "r1"
    classTwo = "c2"
    relTwo = "r2"
    relTypeOne = TO_MANY
    relTypeTwo = TO_ONE

    def setUp(self):
        self.rs = RelationshipSchema(self.classOne, self.relOne, self.relTypeOne,
                            self.classTwo, self.relTwo, self.relTypeTwo)
        
    def tearDown(self):
        self.rs = None 
    
    def testSetRemoteAtt(self):
        self.failUnless(self.rs.remoteAtt(self.relOne) == self.relTwo)

    def testSetRemoteAtt2(self):
        self.failUnless(self.rs.remoteAtt(self.relTwo) == self.relOne)   

    def testSetRemoteClass(self):
        self.failUnless(self.rs.remoteClass(self.relOne) == self.classTwo)
    
    def testSetRemoteClass2(self):
        self.failUnless(self.rs.remoteClass(self.relTwo) == self.classOne)

    def testSetRemoteType(self):
        self.failUnless(self.rs.remoteType(self.relOne) == self.relTypeTwo)
        
    def testSetRemoteType2(self):
        self.failUnless(self.rs.remoteType(self.relTwo) == self.relTypeOne)
        
    def testSetRelType(self):
        self.failUnless(self.rs.relType(self.relOne) == self.relTypeOne)
        
    def testSetRelType2(self):
        self.failUnless(self.rs.relType(self.relTwo) == self.relTypeTwo)
        
    def testGetClass(self):
        self.failUnless(self.rs.classOne() == self.classOne)

    def testGetClass2(self):
        self.failUnless(self.rs.classTwo() == self.classTwo)
    
    def testGetClass(self):
        self.failUnless(self.rs.relOne() == self.relOne)

    def testGetClass2(self):
        self.failUnless(self.rs.relTwo() == self.relTwo)

if __name__ == "__main__":
    unittest.main()
