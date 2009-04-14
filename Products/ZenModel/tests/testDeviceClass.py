###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
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

from zExceptions import Redirect

from Products.ZenModel.Exceptions import *
from Products.ZenModel.DeviceClass import *
from Products.ZenModel.Device import Device

from ZenModelBaseTest import ZenModelBaseTest

class TestDeviceClass(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        devices = self.dmd.Devices
        self.routers = devices.createOrganizer("/NetworkDevice/Router")
        devices.createOrganizer("/NetworkDevice/Router/Firewall")
        devices.createOrganizer("/NetworkDevice/Router/RSM")
        devices.createOrganizer("/Server")
        self.dev = self.dmd.Devices.createInstance("testdev")
        self.dev2 = self.dmd.Devices.createInstance("testdev2")
        self.dev3 = self.routers.createInstance("testrouter")

    def testCreateInstanceDevice(self):
        devices = self.dmd.Devices
        self.assert_(isinstance(self.dev, Device))
        self.assertEqual(self.dev.deviceClass(), devices)
        self.assertEqual(self.dev.getDeviceClassName(), "/")
        self.assertEqual(devices.countDevices(), 3)
        self.assert_(self.dev in devices.getSubDevices())
        self.assertEqual(devices.getPythonDeviceClass(), Device)

    
    def testCreateInstanceDeviceAndIndex(self):
        devices = self.dmd.Devices
        self.assert_(isinstance(self.dev, Device))
        self.assertEqual(self.dev.deviceClass(), devices)
        self.assertEqual(self.dev.getDeviceClassName(), "/")


    def testSearchDevicesOneDevice(self):
        devices = self.dmd.Devices
        self.assertRaises(Redirect, devices.searchDevices, "testdev2",
                          REQUEST=dict(junk=1))

    
    def testSearchDevicesNoDevice(self):
        devices = self.dmd.Devices
        self.assertEqual(len(devices.searchDevices("adsf")), 0)

    
    def testSearchDevicesMultipleDevices(self):
        devices = self.dmd.Devices
        self.assertEqual(len(devices.searchDevices("testdev*")), 2)
        
    def testFindExact(self):
        
        id = 'testdev'
        devices = self.dmd.Devices
        devices.createInstance('TESTDEV')
        #inexact        
        self.assertEqual(len(devices._findDevice(id)), 2)
        #exact
        dev = devices.findDeviceExact(id)
        self.assertEqual( dev.id, id )
        
        self.assert_( not devices.findDeviceExact(None) )
        self.assert_( not devices.findDeviceExact('badid') )

    def testGetPeerDeviceClassNames(self):
        dcnames = self.dev3.getPeerDeviceClassNames()
        self.assert_("/NetworkDevice/Router" in dcnames)
        self.assert_("/NetworkDevice/Router/Firewall" in dcnames)
        self.assert_("/NetworkDevice/Router/RSM" in dcnames)

        self.routers.moveDevices('/','testrouter')
        self.assert_(self.dev3 in self.dmd.Devices.getSubDevices())
        self.assert_(self.dev3 not in 
            self.dmd.Devices.NetworkDevice.Router.getSubDevices())
                        

    def testZPythonClass(self):
        from Products.ZenModel.tests.CustDevice import CustDevice
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        self.assertEqual(CustDevice, 
                     self.dmd.Devices.CustDev.getPythonDeviceClass())

    def testMoveDevices(self):
        self.dmd.Devices.moveDevices('/Server', 'testdev')
        dev = self.dmd.Devices.Server.devices.testdev
        self.assert_(dev.os.interfaces)

    def testMoveDevicesWithPotentialCaseIssue(self):
        self.dmd.Devices.createInstance( 'TESTDEV' )
        self.dmd.Devices.moveDevices('/Server', 'testdev')
        dev = self.dmd.Devices.Server.devices.testdev
        self.assert_(dev.os.interfaces)

    def testMoveDevicesStandardToCust(self):
        anna = self.dmd.Locations.createOrganizer("Annapolis")
        group = self.dmd.Groups.createOrganizer("TestGroup")
        self.dev.setLocation("/Annapolis")
        self.dev.setGroups("/TestGroup")
        self.dev.rackSlot = 15
        from Products.ZenModel.tests.CustDevice import CustDevice
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        self.dmd.Devices.moveDevices('/CustDev', 'testdev') 
        dev = self.dmd.Devices.findDevice('testdev')
        self.assertEqual(dev.getDeviceClassPath(), "/CustDev")
        self.assertEqual(dev.rackSlot, '15')
        self.assertEqual(dev.__class__, CustDevice)
        self.assertEqual(dev.location(), anna)
        self.assert_(dev in anna.devices())
        self.assert_(group in dev.groups())

    def testMoveDevicesCustToStandard(self):
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        cdev = self.dmd.Devices.CustDev.createInstance('cdev')
        anna = self.dmd.Locations.createOrganizer("Annapolis")
        group = self.dmd.Groups.createOrganizer("TestGroup")
        cdev.setLocation("/Annapolis")
        cdev.setGroups("/TestGroup")
        cdev.rackSlot = 15
        self.dmd.Devices.moveDevices("/", 'cdev')
        dev = self.dmd.Devices.findDevice('cdev')
        self.assertEqual(dev.getDeviceClassPath(), "/")
        self.assertEqual(dev.rackSlot, '15')
        self.assertEqual(dev.__class__, Device)
        self.assertEqual(dev.location(), anna)
        self.assert_(group in dev.groups())
     
    def testOrganizer(self):
        devices = self.dmd.Devices
        dc = devices.createOrganizer('/Test')
        self.assert_(dc in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        self.assertEqual(devices.countChildren(), 6)
        self.assert_('Test' in devices.childIds())
        self.assert_('/Test' in devices.getOrganizerNames())
        self.assertEqual(devices.getOrganizer('/Test'), dc)
        layer = devices.createOrganizer('/Layer')
        devices.moveOrganizer('Layer',['Test'])
        self.assert_('/Layer' in devices.getOrganizerNames())
        self.assert_(dc not in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        devices.manage_deleteOrganizers(['/Layer'])
        self.assert_(layer not in devices.children())
        self.assert_(dc not in devices.getSubOrganizers())

    def testDeviceOrganizer(self):
        devices = self.dmd.Devices
        dc = devices.createOrganizer('/Test')
        self.assertEqual(devices.countDevices(), 3)
        self.assert_(self.dev in devices.getSubDevices())

    def test_devtypes(self):
        devices = self.dmd.Devices
        # Test registration
        devices.register_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [('Device', 'SNMP')])
        # Test no duplicates
        devices.register_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [('Device', 'SNMP')])
        # Test removal
        devices.unregister_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [])
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceClass))
    return suite

if __name__=="__main__":
    framework()
