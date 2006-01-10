#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenUtils.ZeoConn import ZeoConn

zeoconn = ZeoConn()

class DeviceTest(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testcreateInstanceDevice(self):
        from Products.ZenModel.Device import Device
        devices = self.dmd.Devices
        dev = devices.createInstance("testdev")
        self.assert_(isinstance(dev, Device))
        self.assert_(dev.deviceClass() == devices)
        self.assert_(dev.getDeviceClassName() == "/")
    
                            
    def testIpRouteCreation(self):
        from Products.ZenModel.IpRouteEntry import IpRouteEntry
        dev = self.dmd.Devices.createInstance("testdev")
        ipr = IpRouteEntry("1.2.3.4_24")
        dev.os.routes._setObject(ipr.id, ipr)
        ipr = dev.os.routes._getOb(ipr.id) 
        ipr.setTarget("1.2.3.4/24")
        self.assert_(ipr.getTarget() == "1.2.3.0/24")
        net = ipr.target()
        self.assert_(ipr in net.clientroutes())
        
        
    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
