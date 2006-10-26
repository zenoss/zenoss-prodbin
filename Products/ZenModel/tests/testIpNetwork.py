import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import logging

from Products.ZenModel.Exceptions import *

from ZenModelBaseTest import ZenModelBaseTest

class TestIpNetwork(ZenModelBaseTest):


    def testIpNetCreation(self):
        net = self.dmd.Networks.createNet("1.2.3.0/24")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)
        net = self.dmd.Networks.createNet('2.3.4.0',24)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)
        
        
    def testIpNetCreation2(self):
        net = self.dmd.Networks.createNet("1.2.3.4/24")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)
        net = self.dmd.Networks.createNet('2.3.4.5',24)
        self.assert_('2.3.4.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)
        
        
    def testIpCreation(self):
        ipobj = self.dmd.Networks.createIp("1.2.3.4", 24)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        #net = self.dmd.Networks._getOb("1.2.3.0")
        #self.assert_(ipobj.network() == net)
        #preceding lines don't work now; don't know why
        

    def testGetNet(self):
        net = self.dmd.Networks.createNet('1.2.3.4/24')
        self.assert_(self.dmd.Networks.getNet('1.2.3.4') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.3.8') == net)
        self.assert_(self.dmd.Networks.getNet('1.2.4.5') == None)


    def testAddIp(self):
        net = self.dmd.Networks.createNet('1.2.3.0/24')
        ipobj0 = self.dmd.Networks.addIp('1.2.3.4')
        self.assert_(self.dmd.Networks.findIp('1.2.3.4') == ipobj0)
        self.assert_(self.dmd.Networks.findIp('1.2.3.5') == None)
        net = self.dmd.Networks.createNet('2.3.4.0/24')
        ipobj1 = self.dmd.Networks.addIp('2.3.4.5')
        self.assert_(self.dmd.Networks.findIp('2.3.4.5') == ipobj1)
        self.assert_(net.findIp('2.3.4.5') == ipobj1)
        self.assert_(net.findIp('1.2.3.4') == ipobj0)


    def testMisc(self):
        net = self.dmd.Networks.createNet('1.2.3.0/24')
        self.dmd.Networks.addIp('1.2.3.4')
        import pdb;pdb.set_trace()
        self.assert_(net.freeIps() == 253)
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
        
        subNet = net.getSubNetwork('1.2.3.0')
        import pdb;pdb.set_trace()
        self.assert_(subNet in net.getSubNetworks())
        
        subNet = net.getSubNetwork('1.2.4.0')
        self.assert_(subNet not in net.getSubNetworks())

        subNet = net.addSubNetwork('1.2.4.0',24)
        self.assert_(subNet in net.getSubNetworks())
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpNetwork))
    return suite

if __name__=="__main__":
    framework()
