#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest
import transaction

import Globals
from Acquisition import aq_base

from Products.ZenRelations.tests.TestSchema import *

from Products.ZenRelations.Exceptions import *

from Testing.ZopeTestCase import ZopeLite

class ZenPropertyManagerTest(unittest.TestCase):


    def setUp(self):
        self.app = ZopeLite.app()
        ZopeLite.installProduct("ZenRelations")
        self.dataroot = self.create(self.app, DataRoot, "dataroot")
        self.dataroot.zPrimaryBasePath = ("",)
        self.orgroot = self.create(self.app.dataroot, Organizer, "Orgs")
        self.orgroot.buildOrgProps()


    def tearDown(self):
        transaction.abort()
        self.app._p_jar.close()
        self.app = None


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        return create(context, klass, id)


    def testZenPropertyIds(self):
        self.assert_(self.orgroot.zenPropertyIds() == 
            ["zenBool", "zenFloat", "zenInt", "zenLines", "zenString"])


    def testZenProperyIdsSubNode(self):
        """Get only ids of a sub node not root"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zenString", "teststring")
        self.assert_(subnode.zenPropertyIds() == ["zenString"])
  

    def testZenProperyIdsSubNodeAll(self):
        """Get all ids from a sub node"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zenString", "teststring")
        self.assert_(subnode.zenPropertyIds() ==
            ["zenBool", "zenFloat", "zenInt", "zenLines", "zenString"])
    
    
    def testZenProperyIdsSubNode(self):
        """Get only ids of a sub node not root"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zenString", "teststring")
        self.assert_(subnode.zenPropertyPath("zenString") == "/SubOrg")
  

    def testSetZenProperyString(self):
        """Set the value of a zenProperty with type string"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenString", "teststring")
        self.assert_(subnode.zenString == "teststring")

    
    def testSetZenProperyInt(self):
        """Set the value of a zenProperty with type int"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenInt", "1")
        self.assert_(subnode.zenInt == 1)
  

    def testSetZenProperyFloat(self):
        """Set the value of a zenProperty with type float"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenFloat", "1.2")
        self.assert_(subnode.zenFloat == 1.2)
  
    
    def testSetZenProperyLines(self):
        """Set the value of a zenProperty with type float"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenLines", "1, 2, 3")
        self.assert_(subnode.zenLines == ["1","2","3"])
  

    def testSetZenProperyBool(self):
        """Set the value of a zenProperty with type boolean"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenBool", "False")
        self.assert_(subnode.zenBool == False)
        subnode.setZenProperty("zenBool", "True")
        self.assert_(subnode.zenBool == True)
  
    
    def testdeleteZenPropery(self):
        """Set delete a zenProperty from a sub node"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zenBool", False)
        self.assert_(subnode.zenBool == False)
        subnode.deleteZenProperty("zenBool")
        self.failIf(hasattr(aq_base(subnode), "zenBool"))
        self.assert_(subnode.zenPropertyPath("zenBool") == "/")


def test_suite():
    return unittest.makeSuite(ZenPropertyManagerTest)

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
        
