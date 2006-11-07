#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import os, sys
if __name__ == '__main__':
  execfile(os.path.join(sys.path[0], 'framework.py'))

from Acquisition import aq_base

from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.Exceptions import *

from ZenRelationsBaseTest import ZenRelationsBaseTest


class ZenPropertyManagerTest(ZenRelationsBaseTest):


    def setUp(self):
        ZenRelationsBaseTest.setUp(self)
        self.orgroot = self.create(self.dmd, Organizer, "Orgs")
        self.orgroot.buildOrgProps()


    def testZenPropertyIds(self):
        self.assert_(self.orgroot.zenPropertyIds() ==
            ["zBool", "zFloat", "zInt", "zLines", "zString"])


    def testZenProperyIdsSubNode(self):
        """Get only ids of a sub node not root"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zString", "teststring")
        self.assert_(subnode.zenPropertyIds() == ["zString"])
  

    def testZenProperyIdsSubNodeAll(self):
        """Get all ids from a sub node"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zenString", "teststring")
        self.assert_(subnode.zenPropertyIds() ==
            ["zBool", "zFloat", "zInt", "zLines", "zString"])
    
    
    def testZenProperyIdsSubNode(self):
        """Get only ids of a sub node not root"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zString", "teststring")
        self.assert_(subnode.zenPropertyPath("zString") == "/SubOrg")
  

    def testSetZenProperyString(self):
        """Set the value of a zenProperty with type string"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zString", "teststring")
        self.assert_(subnode.zString == "teststring")

    
    def testSetZenProperyInt(self):
        """Set the value of a zenProperty with type int"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zInt", "1")
        self.assert_(subnode.zInt == 1)
  

    def testSetZenProperyFloat(self):
        """Set the value of a zenProperty with type float"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zFloat", "1.2")
        self.assert_(subnode.zFloat == 1.2)
  
    
    def testSetZenProperyLines(self):
        """Set the value of a zenProperty with type float"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zLines", "1\n2\n3")
        self.assert_(subnode.zLines == ["1","2","3"])
  

    def testSetZenProperyBool(self):
        """Set the value of a zenProperty with type boolean"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zBool", "False")
        self.assert_(subnode.zBool == False)
        subnode.setZenProperty("zBool", "True")
        self.assert_(subnode.zBool == True)
  
    
    def testdeleteZenPropery(self):
        """Set delete a zenProperty from a sub node"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zBool", False)
        self.assert_(subnode.zBool == False)
        subnode.deleteZenProperty("zBool")
        self.failIf(hasattr(aq_base(subnode), "zBool"))
        self.assert_(subnode.zenPropertyPath("zBool") == "/")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ZenPropertyManagerTest))
    return suite

if __name__=="__main__":
    framework()
        
