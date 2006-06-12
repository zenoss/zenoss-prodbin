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

class TestDevice(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance("testdev")


    def tearDown(self):
        transaction.abort()
        self.dmd = None


    def testcreateInstanceDevice(self):
        from Products.ZenModel.Device import Device
        devices = self.dmd.Devices
        self.assert_(isinstance(self.dev, Device))
        self.assert_(self.dev.deviceClass() == devices)
        self.assert_(self.dev.getDeviceClassName() == "/")
    
                            
    def testIpRouteCreation(self):
        from Products.ZenModel.IpRouteEntry import IpRouteEntry
        ipr = IpRouteEntry("1.2.3.4_24")
        self.dev.os.routes._setObject(ipr.id, ipr)
        ipr = self.dev.os.routes._getOb(ipr.id) 
        ipr.setTarget("1.2.3.4/24")
        self.assert_(ipr.getTarget() == "1.2.3.0/24")
        net = ipr.target()
        self.assert_(ipr in net.clientroutes())
        

    def testSetLocation(self):
        self.dev.setLocation('/Test/Loc')
        self.assert_(self.dev.getLocationName() == '/Test/Loc')

    
    def testAddLocation(self):
        self.dev.addLocation('/Test')
        self.assert_("/Test" in self.dmd.Locations.getOrganizerNames())


    def testSetStatusMonitors(self):
        self.dev.setStatusMonitors(['test1','test2'])
        smms = self.dev.getStatusMonitorNames()
        self.assert_('test1' in smms)
        self.assert_('test2' in smms)
        self.dev.setStatusMonitors(['test1'])
        smms = self.dev.getStatusMonitorNames()
        self.assert_('test1' in smms)
        self.assert_('test2' not in smms)
        self.dev.setStatusMonitors(['test3'])
        smms = self.dev.getStatusMonitorNames()
        self.assert_('test3' in smms)
        self.assert_('test1' not in smms)
        
    
def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
