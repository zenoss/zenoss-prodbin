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
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.MibOrganizer import *

from ZenModelBaseTest import ZenModelBaseTest


class TestMibOrganizer(ZenModelBaseTest):


    def testMibOrganizer(self):
        mibOrg = self.dmd.Mibs
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
        mibOrg = self.dmd.Mibs
        mod = mibOrg.createMibModule('mod')

        self.assert_(mod.getModuleName() == 'mod')

        mod.createMibNode(id = 'node', moduleName = 'mod', nodetype = 'MibNode'\
                          , oid = '1', status = 'ok', description = 'my mib'\
                         )
                         
        self.assert_(mod.nodeCount() == 1)
        self.assert_(mibOrg.name2oid('node') == '1')
        self.assert_(mibOrg.oid2name('1') == 'node')
        
        mod.createMibNotification(id = 'notification', moduleName = 'mod',\
                                  nodetype = 'MibNotification', oid = '2',\
                                  status = 'ok', description = 'my note'\
                                 )
        
        self.assert_(mod.notificationCount() == 1)
        self.assert_(mibOrg.name2oid('notification') == '2')
        self.assert_(mibOrg.oid2name('2') == 'notification')


    def testOrganizer(self):
        mibOrg = self.dmd.Mibs
        subOrg = mibOrg.createOrganizer('/sub')
        mod = mibOrg.createMibModule('mod', '/modLoc')
        modLoc = mibOrg.getOrganizer('modLoc')
        moveMe = mibOrg.createOrganizer('/mobile')
        # there's more in mibOrg than is defined here, due to the test case
        # setup
        self.assert_(mibOrg.countChildren() == 3)
        self.assert_(subOrg in mibOrg.getSubOrganizers())
        self.assert_(modLoc in mibOrg.getSubOrganizers())
        self.assert_('/sub' in mibOrg.getOrganizerNames())
        self.assert_('/modLoc' in mibOrg.getOrganizerNames())
        mibOrg.moveOrganizer('/sub', ['mobile'])
        self.assert_(moveMe not in mibOrg.children())
        self.assert_(moveMe in subOrg.children())
        mibOrg.manage_deleteOrganizers(['sub','modLoc'])
        self.assert_(subOrg not in mibOrg.getSubOrganizers())
        self.assert_(modLoc not in mibOrg.getSubOrganizers())
        self.assert_(moveMe not in mibOrg.getSubOrganizers())
        self.assert_(mibOrg.countClasses() == 0)
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMibOrganizer))
    return suite

if __name__=="__main__":
    framework()
