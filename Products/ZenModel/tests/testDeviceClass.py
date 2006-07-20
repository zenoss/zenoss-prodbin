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
from Products.ZenModel.Device import Device

from ZenModelBaseTest import ZenModelBaseTest

from Testing.ZopeTestCase import ZopeLite
from Testing.ZopeTestCase.ZopeTestCase import ZopeTestCase, user_role, \
                                    folder_name, standard_permissions

class TestDeviceClass(ZenModelBaseTest):


    def testCreateInstanceDevice(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()#necessary, don't know why
        dev = devices.createInstance("testdev")
        self.assert_(isinstance(dev, Device))
        self.assert_(dev.deviceClass() == devices)
        self.assert_(dev.getDeviceClassName() == "/")
        self.assert_(devices.countDevices() == 1)
        self.assert_(dev in devices.getSubDevices())
        self.assert_(devices.getPythonDeviceClass() == Device)

    
    def testCreateInstanceDeviceAndIndex(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assert_(isinstance(dev, Device))
        self.assert_(dev.deviceClass() == devices)
        self.assert_(dev.getDeviceClassName() == "/")


    def testSearchDevicesOneDevice(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assertRaises(Redirect, devices.searchDevices, "testdev")

    
    def testSearchDevicesNoDevice(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        self.assert_(len(devices.searchDevices("adsf"))==0)

    
    def testSearchDevicesMultipleDevices(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()
        dev = devices.createInstance("testdev")
        dev = devices.createInstance("testdev2")
        self.assert_(len(devices.searchDevices("testdev*"))==2)

    
    def testGetPeerDeviceClassNames(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        routers = devices.createOrganizer("/NetworkDevice/Router")
        devices.createOrganizer("/NetworkDevice/Router/Firewall")
        devices.createOrganizer("/NetworkDevice/Router/RSM")
        devices.createOrganizer("/Server")
        devices.createCatalog()
        dev = routers.createInstance("testrouter")
        dcnames = dev.getPeerDeviceClassNames()
        
        self.assert_("/NetworkDevice/Router" in dcnames)
        self.assert_("/NetworkDevice/Router/Firewall" in dcnames)
        self.assert_("/NetworkDevice/Router/RSM" in dcnames)
        #self.assert_("/Server" not in dcnames)FIXME: should it be in here or
        #                                             not?

        routers.moveDevices('/','testrouter')

        self.assert_(dev in self.dmd.Devices.getSubDevices())
        self.assert_(dev not in self.dmd.Devices.NetworkDevice.Router.getSubDevices())
                        

    def testOrganizer(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        dc = devices.createOrganizer('/Test')
        self.assert_(dc in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        self.assert_(devices.countChildren() == 1)
        self.assert_('Test' in devices.childIds())
        self.assert_('/Test' in devices.getOrganizerNames())
        self.assert_(devices.getOrganizer('/Test') == dc)
        layer = devices.createOrganizer('/Layer')
        devices.moveOrganizer('Layer',['Test']) 
        self.assert_('/Layer' in devices.getOrganizerNames())
        self.assert_(dc not in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        devices.manage_deleteOrganizers(['/Layer'])
        self.assert_(layer not in devices.children())
        self.assert_(dc not in devices.getSubOrganizers())


    def testDeviceOrganizer(self):
        devices = self.create(self.dmd, DeviceClass, 'Devices')
        devices.createCatalog()
        dev = devices.createInstance('testdev')
        dc = devices.createOrganizer('/Test')
        self.assert_(devices.countDevices() == 1)
        self.assert_(dev in devices.getSubDevices())
        

def main():
    unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
    unittest.main()
