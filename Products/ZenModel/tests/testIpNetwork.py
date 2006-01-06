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
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        
        
    def testIpNetCreation2(self):
        net = self.dmd.Networks.createNet("1.2.3.4/24")
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        
        
    def testIpCreation(self):
        ipobj = self.dmd.Networks.createIp("1.2.3.4", 24)
        self.assert_("1.2.3.0" in self.dmd.Networks.objectIds())
        net = self.dmd.Networks._getOb("1.2.3.0")
        self.assert_(ipobj.network() == net)
        
        
    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
