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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(ZenPropertyManagerTest))
    return suite

if __name__=="__main__":
    framework()
        
