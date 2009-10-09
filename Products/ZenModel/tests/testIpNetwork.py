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
        
    def testCreateIpWithLessSpecificMask(self):
        """
        See ticket #3646.
        
        Add network 42.67.128.0/17, then create IP address 42.67.129.14 with a
        netmask of 3.  The important thing is that the netmask of the IP
        address has a less specific mask length than the network.  The IP
        address should be created directly under the network.
        """
        dmdNet = self.dmd.Networks
        # set this explicitly to the default. it should not affect this test.
        # but it is used by createIp, so just to be safe.
        dmdNet._updateProperty('zDefaultNetworkTree', (24, 32))
        
        subnet = dmdNet.addSubNetwork("42.67.128.0", 17)
        # make sure it is in the right place
        self.assertEqual(subnet, dmdNet._getOb("42.67.128.0"))
        # make sure it has the right netmask
        self.assertEqual(17, subnet.netmask)
        
        ip = dmdNet.createIp("42.67.129.14", 3)
        # make sure the IP address has the correct netmask
        self.assertEqual(3, ip.netmask)
        # make sure the subnet still has the right netmask
        self.assertEqual(17, subnet.netmask)
        # make sure the IP address is in the right place
        msg = "42.67.129.14 should be in subnet.ipaddresses(), but it is " \
              "not. subnet.ipaddresses() = %s" % subnet.ipaddresses()
        self.assert_(ip in subnet.ipaddresses(), msg)
        # make sure no new networks have been created under the subnet
        self.assertEqual([], subnet.children())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpNetwork))
    return suite

if __name__=="__main__":
    framework()
