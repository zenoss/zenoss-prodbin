#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import pdb
import unittest

import Globals

from Products.ZenModel.Exceptions import *
from Products.ZenModel.DeviceClass import *

from ZenModelBaseTest import ZenModelBaseTest

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
        self.assert_(len(devices.searchDevices("testdev")) == 1)
        self.assert_(devices.searchDevices("testdev")[0] == dev)

    
                            

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
