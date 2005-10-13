#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals

from zExceptions import Redirect

from Products.ZenModel.Exceptions import *
from Products.ZenModel.DeviceClass import *

from ZenModelBaseTest import ZenModelBaseTest

from Testing.ZopeTestCase import ZopeLite
from Testing.ZopeTestCase.ZopeTestCase import ZopeTestCase, user_role, \
                                    folder_name, standard_permissions

class DeviceClassTest(ZenModelBaseTest):


    def testcreateInstanceDevice(self):
        from Products.ZenModel.Device import Device
        devices = self.create(self.dmd, DeviceClass, "Devices")
        dev = devices.createInstance("testdev")
        self.assert_(isinstance(dev, Device))
        self.assert_(dev.deviceClass() == devices)
        self.assert_(dev.getDeviceClassName() == "/")

    
    def testcreateInstanceRouter(self):
        from Products.ZenModel.Router import Router
        devices = self.create(self.dmd, DeviceClass, "Devices")
        routers = devices.createOrganizer("/NetworkDevice/Router")
        dev = routers.createInstance("testrouter")
        self.assert_(isinstance(dev, Router))
        self.assert_(dev.deviceClass() == routers)
        self.assert_(dev.getDeviceClassName() == "/NetworkDevice/Router")

    
    def testcreateInstanceDeviceAndIndex(self):
        from Products.ZenModel.Device import Device
        devices = self.create(self.dmd, DeviceClass, "Devices")
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assert_(isinstance(dev, Device))
        self.assert_(dev.deviceClass() == devices)
        self.assert_(dev.getDeviceClassName() == "/")


    def testSearchDevicesOneDevice(self):
        devices = self.create(self.dmd, DeviceClass, "Devices")
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assertRaises(Redirect, devices.searchDevices, "testdev")

    
    def testSearchDevicesNoDevice(self):
        devices = self.create(self.dmd, DeviceClass, "Devices")
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assert_(len(devices.searchDevices("adsf"))==0)

    
    def testSearchDevicesMultipleDevices(self):
        devices = self.create(self.dmd, DeviceClass, "Devices")
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        dev = devices.createInstance("testdev2")
        self.assert_(len(devices.searchDevices("testdev*"))==2)

    
    def testGetPeerDeviceClassNames(self):
        devices = self.create(self.dmd, DeviceClass, "Devices")
        routers = devices.createOrganizer("/NetworkDevice/Router")
        devices.createOrganizer("/NetworkDevice/Router/Firewall")
        devices.createOrganizer("/NetworkDevice/Router/RSM")
        devices.createOrganizer("/Server")
        dev = routers.createInstance("testrouter")
        dcnames = dev.getPeerDeviceClassNames()
        self.assert_("/NetworkDevice/Router" in dcnames)
        self.assert_("/NetworkDevice/Router/Firewall" in dcnames)
        self.assert_("/NetworkDevice/Router/RSM" in dcnames)
        self.assert_("/Server" not in dcnames)
                        
                            

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
