###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
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

from Products.ZenModel.Exceptions import *

from ZenModelBaseTest import ZenModelBaseTest

class TestIpNetwork(ZenModelBaseTest):


    def testIpNetCreation(self):
        "Create valid networks"
        net = self.dmd.Networks.createNet("1.2.3.0/24")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)
        net = self.dmd.Networks.createNet('2.3.4.0',24)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)
        
        
    def testBadIpNetCreation(self):
        "Test evil network masks"
        net = self.dmd.Networks.createNet("1.2.3.4/24", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',None)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',-1)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet('2.3.4.5',64)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4////24", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4/evil", None)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        net = self.dmd.Networks.createNet("1.2.3.4", "more evil")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)

        
        
    def testIpCreation(self):
        ipobj = self.dmd.Networks.createIp("1.2.3.4", 24)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        net = self.dmd.Networks._getOb("1.2.3.0")
        self.assert_(ipobj.network() == net)
        

    def testGetNet(self):
        net = self.dmd.Networks.createNet('1.2.3.4/24')
        self.assert_(self.dmd.Networks.getNet('1.2.3.4') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.3.8') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.4.5') == None)


    def testMisc(self):
        net = self.dmd.Networks.createNet('1.2.3.0/24')
        self.assert_(net.freeIps() == 254)
        self.dmd.Networks.createIp('1.2.3.4')
        self.assert_(net.freeIps() == 253)
        self.assert_(net.countIpAddresses(inuse=False) == 1)
        self.assert_(net.getNetworkName() == '1.2.3.0/24')
        self.assert_(not net.getIpAddress('1.2.3.4') == None)
        self.assert_(net.getIpAddress('1.2.3.5') == None)
        self.assert_(self.dmd.Networks.getIpAddress('1.2.3.4') == None)
        self.assert_(net.defaultRouterIp() == '1.2.3.1')
        ipobj = net.addIpAddress('1.2.3.5')
        self.assert_(ipobj in net.ipaddresses())

    
    def testSubNetworks(self):
        dmdNet = self.dmd.Networks
        dmdNet.createNet('1.2.3.0/24')
        net = dmdNet.getSubNetwork('1.2.3.0')
        self.assert_(net in dmdNet.getSubNetworks())
        subNet = dmdNet.addSubNetwork('1.2.4.0',24)
        self.assert_(subNet in dmdNet.getSubNetworks())


    def testAutomaticNesting(self):
        dmdNet = self.dmd.Networks
        dmdNet.zDefaultNetworkTree = ['24', '32']
        dmdNet.createNet('1.2.0.0/16')
        dmdNet.createNet('1.2.3.0/24')
        net = dmdNet.findNet('1.2.0.0')
        subnet = dmdNet.findNet('1.2.3.0')
        self.assert_(subnet in net.children())


    def testAutomaticNesting2(self):
        dmdNet = self.dmd.Networks
        dmdNet.zDefaultNetworkTree = ['8', '16', '24', '32']
        dmdNet.createNet('1.2.3.0/24')
        dmdNet.createNet('1.2.4.0/24')
        net = dmdNet.findNet('1.2.0.0')
        self.assert_(dmdNet.findNet('1.2.3.0') in net.children())
        self.assert_(dmdNet.findNet('1.2.4.0') in net.children())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpNetwork))
    return suite

if __name__=="__main__":
    framework()
