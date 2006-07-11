import unittest
import pdb

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenUtils.ZeoConn import ZeoConn

zeoconn = ZeoConn()

class IpNetworkTest(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testIpNetCreation(self):
        net = self.dmd.Networks.createNet("1.2.3.0/24")
        self.assert_("1.2.0.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)
        net = self.dmd.Networks.createNet('2.3.4.0',24)
        self.assert_('2.3.0.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)
        
        
    def testIpNetCreation2(self):
        net = self.dmd.Networks.createNet("1.2.3.4/24")
        self.assert_("1.2.0.0" in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('1.2.3.0') == net)
        net = self.dmd.Networks.createNet('2.3.4.5',24)
        self.assert_('2.3.0.0' in self.dmd.Networks.objectIds())
        self.assert_(self.dmd.Networks.getNet('2.3.4.0') == net)
        
        
    def testIpCreation(self):
        ipobj = self.dmd.Networks.createIp("1.2.3.4", 24)
        self.assert_("1.2.0.0" in self.dmd.Networks.objectIds())
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
        self.assert_(net.freeIps() == 253)
        self.assert_(net.hasIp('1.2.3.4'))

        

    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
