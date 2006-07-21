#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals

from ZenModelBaseTest import ZenModelBaseTest

from Products.ZenModel.Exceptions import *

from Products.ZenModel.MibOrganizer import *

class TestMibOrganizer(ZenModelBaseTest):


    def testMibOrganizer(self):
        mibOrg = self.create(self.dmd, MibOrganizer, 'Mibs') 
        mod = mibOrg.createMibModule('mod')
        two = mibOrg.createMibModule('two','/layer')
        self.assert_(mod in mibOrg.mibs())
        self.assert_(mibOrg.countClasses() == 2)
        self.assert_('layer' in mibOrg.childIds())
        layer = mibOrg.getOrganizer('layer')
        self.assert_(two in layer.mibs())
        layer.moveMibModules('/',['two'])
        self.assert_(two not in layer.mibs())
        self.assert_(two in mibOrg.mibs())
        mibOrg.removeMibModules(['two'])
        self.assert_(two not in mibOrg.mibs())
        three = mibOrg.manage_addMibModule('three')
        self.assert_(three in mibOrg.mibs())
        

    def testMibModule(self):
        mibOrg = self.create(self.dmd, MibOrganizer, 'Mibs')
        mod = mibOrg.createMibModule('mod')
        mod.createMibNode(id = 'node', moduleName = 'mod', nodetype = 'MibNode',                          oid = '1', status = 'ok', description = 'my mib')
        self.assert_(mibOrg.name2oid('node') == '1')
        self.assert_(mibOrg.oid2name('1') == 'node')
        self.assert_(mod.getModuleName() == 'mod')
        self.assert_(mod.nodeCount() == 1)
        

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
