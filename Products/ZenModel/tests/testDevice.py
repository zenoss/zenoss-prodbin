#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest

import transaction

from Products.ZenModel.Exceptions import *

from ZenModelBaseTest import ZenModelBaseTest

class TestDevice(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance("testdev")


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
        self.dev.addLocation('/Test/Loc')
        self.assert_('/Test/Loc' in self.dmd.Locations.getOrganizerNames())


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

    
    def testSetHWSerialNumber(self):
        self.dev.setHWSerialNumber('testKey')
        self.assert_(self.dev.getHWSerialNumber() == 'testKey')
    

    def testSetOSProductKey(self):
        unicodeificated = 'ab\xefcd'.decode('latin1')
        self.dev.setOSProductKey(unicodeificated)
        self.assert_(self.dev.getOSProductKey() == 'ab_cd')
        
        self.dev.manage_editDevice(osManufacturer='Apple',
                                   osProductName='Macos 10.4.1')
        self.assert_(self.dev.getOSProductKey() == 'Darwin 8.1.0')


    def testSetHWProductKey(self):
        self.dev.setHWProductKey('testKey')
        self.assert_(self.dev.getHWProductKey() == 'testKey')

        self.dev.manage_editDevice(hwManufacturer='HP',
                                   hwProductName='ProLient 800')
        self.assert_(self.dev.getHWProductKey() == 'ProLient 800')


    def testSetLastChange(self):
        from DateTime import DateTime
        dt = DateTime()
        self.dev.setLastChange(dt)
        self.assert_(self.dev.getLastChange() == dt)


    def testSetProdState(self):
        self.dev.setProdState(500)
        self.assert_(self.dev.getProductionStateString() == 'Pre-Production')


    def testSetSnmpLastCollection(self):
        from DateTime import DateTime
        dt = DateTime()
        self.dev.setSnmpLastCollection(dt)
        self.assert_(self.dev.getSnmpLastCollection() == dt)


    def testSetHWProduct(self):
        self.dev.setHWProduct('testHW', 'HP')
        self.assert_('testHW' in self.dev.getDmdRoot("Manufacturers")\
                     .getProductNames('HP')\
                    )


    def testSetLastPollSnmpUpTime(self):
        from DateTime import DateTime
        dt = DateTime()
        self.dev.setLastPollSnmpUpTime(dt)
        self.assert_(int(dt) == self.dev.getLastPollSnmpUpTime())


#   def testRenameDevice(self):
#        self.dev.renameDevice('newID')
#        self.assert_(self.dev.getID() == 'newID')


    def testSetOSProduct(self):
        self.dev.setOSProduct('testOS', 'HP')
        self.assert_('testOS' in self.dev.getDmdRoot("Manufacturers")\
                     .getProductNames('HP')\
                    )


    def testAddStatusMonitor(self):
        self.dev.addStatusMonitor('testMon')
        self.assert_('testMon' in\
                     self.dev.getDmdRoot("Monitors").getStatusMonitorNames()\
                    )


    def testAddSystem(self):
        self.dev.addSystem('/test/sys/loc')
        self.assert_('/test/sys/loc' in self.dev.getSystemNames())
        

    def testAddDeviceGroup(self):
        self.dev.addDeviceGroup('/test/dev/grp/loc')
        self.assert_('/test/dev/grp/loc' in self.dev.getDeviceGroupNames())


    def testAddManufacturer(self):
        self.dev.addManufacturer(newHWManufacturerName='testHWMfr')
        self.assert_('testHWMfr' in self.dev.getDmdRoot("Manufacturers").getManufacturerNames())
        self.dev.addManufacturer(newSWManufacturerName='testSWMfr')
        self.assert_('testSWMfr' in self.dev.getDmdRoot("Manufacturers").getManufacturerNames())


   #def testGetOsVersion(self):
   #    self.assert_(self.dev.getOsVersion() == "GET_OS_VERSION_HERE")


    def testGetOSProductName(self):
        self.dev.manage_editDevice(osManufacturer='Apple',
                                   osProductName='Macos 10.4.1')
        self.assert_(self.dev.getOSProductName() == "Macos 10.4.1")
        

    def testSnmpAgeCheck(self):
        import time
        self.dev.setSnmpLastCollection()
        time.sleep(0.1)  #because computers are too fast...
        self.assert_(self.dev.snmpAgeCheck(0) == 1)
        self.assert_(self.dev.snmpAgeCheck(5) == None)


   #def testSetTerminalServer(self):
   #    self.dev.setTerminalServer('iDontExist')


    def testSetGroups(self):
        self.dev.setGroups(['/First/Test/Group','/Second/Test/Group'])
        groupNames = self.dev.getDeviceGroupNames()
        self.assert_('/First/Test/Group' in groupNames)
        self.assert_('/Second/Test/Group' in groupNames)
        self.dev.setGroups(['/First/Test/Group'])
        groupNames = self.dev.getDeviceGroupNames()
        self.assert_('/First/Test/Group' in groupNames)
        self.assert_('/Second/Test/Group' not in groupNames)
        self.dev.setGroups(['/Third/Test/Group'])
        groupNames = self.dev.getDeviceGroupNames()
        self.assert_('/Third/Test/Group' in groupNames)
        self.assert_('/First/Test/Group' not in groupNames)
        self.dev.setGroups([])
        groupNames = self.dev.getDeviceGroupNames()
        self.assert_('/Third/Test/Group' not in groupNames)
        

    def testSetPerformanceMonitor(self):
        self.dev.setPerformanceMonitor('perfMon')
        self.assert_(self.dev.getPerformanceServerName() == 'perfMon')
        self.dev.setPerformanceMonitor('perfMon', 'nextMon')
        self.assert_(self.dev.getPerformanceServerName() == 'nextMon')


    def testMonitorDevice(self):
        self.dev.setProdState(1000)
        self.assert_(self.dev.monitorDevice())
        self.dev.setProdState(250)
        self.assert_(not self.dev.monitorDevice())


    def testSetManageIp(self):
        self.dev.setManageIp('1.2.3.4')
        self.assert_(self.dev.getManageIp() == '1.2.3.4')
        d = self.dmd.Devices.createInstance('localhost')
        d.setManageIp()
        self.assert_(d.getManageIp() == '127.0.0.1')


    def testManage_editDevice(self):
        self.dev.manage_editDevice()

        self.assert_(self.dev.hw.tag == '')
        self.assert_(self.dev.hw.serialNumber == '')
        self.assert_(self.dev.zSnmpCommunity == '')
        self.assert_(self.dev.zSnmpPort == 161)
        self.assert_(self.dev.zSnmpVer == 'v1')
        self.assert_(self.dev.rackSlot == 0)
        self.assert_(self.dev.productionState == 1000)
        self.assert_(self.dev.comments == "")
        self.assert_(self.dev.getHWManufacturerName() == "")
        self.assert_(self.dev.getHWProductName() == "")
        self.assert_(self.dev.getOSManufacturerName() == "")
        self.assert_(self.dev.getOSProductName() == "")
        self.assert_(self.dev.getLocationLink() == "")
        self.assert_(self.dev.getLocationName() == "")
        self.assert_(self.dev.getDeviceGroupNames() == [])
        self.assert_(self.dev.getSystemNames() == [])
        self.assert_('localhost' in self.dev.getStatusMonitorNames())
        self.assert_(self.dev.getPerformanceServerName() == "localhost")

        self.dev.manage_editDevice(tag='tag', serialNumber='SN123',
                        zSnmpCommunity='theHood', zSnmpPort=121, zSnmpVer='v2',
                        rackSlot=1, productionState=1000,
                        comments="cross your fingers", hwManufacturer="HP",
                        hwProductName="hwProd", osManufacturer="Apple",
                        osProductName="osProd", locationPath='/test/loc',
                        groupPaths=['/group/path1','/group/path2'],
                        systemPaths=['/sys/path1','/sys/path2'],
                        statusMonitors=['statMon1','statMon2'],
                        performanceMonitor='perfMon')
                        
        self.assert_(self.dev.hw.tag == 'tag')
        self.assert_(self.dev.hw.serialNumber == 'SN123')
        self.assert_(self.dev.zSnmpCommunity == 'theHood')
        self.assert_(self.dev.zSnmpPort == 121)
        self.assert_(self.dev.zSnmpVer == 'v2')
        self.assert_(self.dev.rackSlot == 1)
        self.assert_(self.dev.productionState == 1000)
        self.assert_(self.dev.comments == "cross your fingers")
        self.assert_(self.dev.getHWManufacturerName() == "HP")
        self.assert_(self.dev.getHWProductName() == "hwProd")
        self.assert_(self.dev.getOSManufacturerName() == "Apple")
        self.assert_(self.dev.getOSProductName() == "osProd")
        self.assert_(self.dev.getLocationLink() == "<a href='/zport/dmd/Locations/test/loc'>/test/loc</a>")
        self.assert_(self.dev.getLocationName() == '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames())
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames())
        self.assert_('/sys/path1' in self.dev.getSystemNames())
        self.assert_('/sys/path2' in self.dev.getSystemNames())
        self.assert_('statMon1' in self.dev.getStatusMonitorNames())
        self.assert_('statMon2' in self.dev.getStatusMonitorNames())
        self.assert_(self.dev.getPerformanceServerName() == "perfMon")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDevice))
    return suite

if __name__=="__main__":
    framework()
