###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os, sys
if __name__ == '__main__':
  execfile(os.path.join(sys.path[0], 'framework.py'))

from Acquisition import aq_base

from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.Exceptions import *

from ZenRelationsBaseTest import ZenRelationsBaseTest
from unittest import TestCase
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRelations.ZenPropertyManager import ZenPropertyManager
from Products.ZenRelations.RelationshipManager import RelationshipManager

class ZenPropertyManagerTest(ZenRelationsBaseTest):


    def setUp(self):
        ZenRelationsBaseTest.setUp(self)
        self.orgroot = self.create(self.dmd, Organizer, "Orgs")
        self.orgroot.buildOrgProps()


    def testZenPropertyIds(self):
        self.assert_(self.orgroot.zenPropertyIds() ==
            ["zBool", "zFloat", "zInt", "zLines", "zString"])


    def testZenPropertyIdsSubNode(self):
        """Get only ids of a sub node not root"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("zString", "teststring")
        self.assert_(subnode.zenPropertyPath("zString") == "/SubOrg")
  

    def testSetZenPropertyString(self):
        """Set the value of a zenProperty with type string"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zString", "teststring")
        self.assert_(subnode.zString == "teststring")

    
    def testSetZenPropertyInt(self):
        """Set the value of a zenProperty with type int"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zInt", "1")
        self.assert_(subnode.zInt == 1)
  

    def testSetZenPropertyFloat(self):
        """Set the value of a zenProperty with type float"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zFloat", "1.2")
        self.assert_(subnode.zFloat == 1.2)
  
    
    def testSetZenPropertyLines(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zLines", ["1", "2", "3"])
        self.assert_(subnode.zLines == ["1","2","3"])
  

    def testSetZenPropertyBool(self):
        """Set the value of a zenProperty with type boolean"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zBool", "False")
        self.assert_(subnode.zBool == False)
        subnode.setZenProperty("zBool", "True")
        self.assert_(subnode.zBool == True)
  
    
    def testdeleteZenProperty(self):
        """Set delete a zenProperty from a sub node"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode.setZenProperty("zBool", False)
        self.assert_(subnode.zBool == False)
        subnode.deleteZenProperty("zBool")
        self.failIf(hasattr(aq_base(subnode), "zBool"))
        self.assert_(subnode.zenPropertyPath("zBool") == "/")


    def testUpdatePropertyLines(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("ptest", ("1", "2", "3"), 'lines')
        subnode._updateProperty('ptest', ('1','2'))
        self.assert_(subnode.ptest == ('1','2'))

    def testUpdatePropertyInt(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("ptest", 1, 'int')
        subnode._updateProperty('ptest', 2)
        self.assert_(subnode.ptest == 2)

    def testUpdatePropertyFloat(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("ptest", 1.2, 'float')
        subnode._updateProperty('ptest', 2.2)
        self.assert_(subnode.ptest == 2.2)

    def testUpdatePropertyBoolean(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("ptest", False, 'boolean')
        subnode._updateProperty('ptest', True)
        self.assert_(subnode.ptest == True)

    def testUpdatePropertyString(self):
        """Set the value of a zenProperty with type lines"""
        subnode = self.create(self.orgroot, Organizer, "SubOrg")
        subnode._setProperty("ptest", 'a', 'string')
        subnode._updateProperty('ptest', 'b')
        self.assert_(subnode.ptest == 'b')

class Transformer(object):
    
    def transformForSet(self, input):
        return 'foo_%s' % input
        
    def transformForGet(self, input):
        return 'bar_%s' % input

class TransformerBase(object):
    
    def tearDown(self):
        self.manager = None
        
    def testMyTestType(self):
        "test that property of type 'my test type' is transformed"
        self.manager._setProperty('quux', 'blah', 'my test type')
        self.assertEqual('bar_foo_blah', self.manager.getProperty('quux'))
        self.manager._updateProperty('quux', 'clash')
        self.assertEqual('bar_foo_clash', self.manager.getProperty('quux'))
        
    def testString(self):
        "test that a string property isn't mucked with"
        self.manager._setProperty('halloween', 'cat')
        self.assertEqual('cat', self.manager.getProperty('halloween'))
        self.assertEqual('cat', self.manager.halloween)
        
    def testNormalAttribute(self):
        "make sure that a normal attribute isn't mucked with"
        self.manager.dog = 'Ripley'
        self.assertEqual('Ripley', self.manager.dog)
        
transformers = {'my test type': Transformer()}

class TransformerTest(TransformerBase, TestCase):
    
    def setUp(self):
        """
        Test ZenPropertyManager that does not acquire a dmd attribute.
        """
        self.manager = ZenPropertyManager()
        self.manager.propertyTransformers = transformers
        
class TransformerDmdTest(TransformerBase, BaseTestCase):
    
    def setUp(self):
        """
        Test getting the transformers dictionary from the well-known dmd
        location.
        """
        BaseTestCase.setUp(self)
        self.dmd.propertyTransformers = transformers
        managerId = 'manager'
        self.dmd._setObject(managerId, RelationshipManager(managerId))
        self.manager = self.dmd.manager
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ZenPropertyManagerTest))
    suite.addTest(makeSuite(TransformerTest))
    suite.addTest(makeSuite(TransformerDmdTest))
    return suite

if __name__=="__main__":
    framework()
        
