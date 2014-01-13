##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import time
import logging
from DateTime import DateTime

from Products.ZenModel.Exceptions import *
from Products.ZenModel.Device import Device, manage_createDevice
from Products.ZenModel.IpRouteEntry import IpRouteEntry
from Products.ZenModel.ZDeviceLoader import BaseDeviceLoader

from ZenModelBaseTest import ZenModelBaseTest


class TestDevice(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestDevice, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        man = self.dmd.Manufacturers
        man.createManufacturer('Apple')
        man.createSoftwareProduct('Macos 10.4.1', 'Apple',
            productKey='Darwin 8.1.0', isOS=True)
        man.createManufacturer('HP')
        man.createHardwareProduct('ProLiant 800', 'HP',
            productKey='ProLiant 800')
        man.createManufacturer('Unknown')


    def testManage_createDevice(self):
        dev = manage_createDevice(self.dmd, 'mydevice', '/')
        self.assert_(isinstance(dev, Device))
        self.assertEqual(dev.deviceClass(), self.dmd.Devices)
        self.assertEqual(dev.getDeviceClassName(), "/")
        self.assertEqual(dev.id, "mydevice")
        self.assertEqual(dev.titleOrId(), "mydevice")

    def testManage_createDeviceWithIdAndTitle(self):
        dev = manage_createDevice(self.dmd, 'mydevice', '/',
                                  title="mydevicetitle")
        self.assert_(isinstance(dev, Device))
        self.assertEqual(dev.deviceClass(), self.dmd.Devices)
        self.assertEqual(dev.getDeviceClassName(), "/")
        self.assertEqual(dev.id, "mydevice")
        self.assertEqual(dev.title, "mydevicetitle")
        self.assertEqual(dev.titleOrId(), "mydevicetitle")

    def testManage_createDeviceDup(self):
        dev = manage_createDevice(self.dmd, 'mydevice', '/')
        self.assertRaises(DeviceExistsError,
                          manage_createDevice, self.dmd, 'mydevice', '/')

    def testManage_createDeviceDupIp(self):
        dev = manage_createDevice(self.dmd, 'mydevice', '/', manageIp='1.1.1.1')
        self.assertRaises(DeviceExistsError,
          manage_createDevice, self.dmd, 'mydevice2', '/', manageIp='1.1.1.1')

    def testIpRouteCreation(self):
        ipr = IpRouteEntry("1.2.3.4_24")
        self.dev.os.routes._setObject(ipr.id, ipr)
        ipr = self.dev.os.routes._getOb(ipr.id)
        ipr.setTarget("1.2.3.4/24")
        self.assertEqual(ipr.getTarget(), "1.2.3.0/24")
        net = ipr.target()
        self.assert_(ipr in net.clientroutes())


    def testSetLocation(self):
        self.dev.setLocation('/Test/Loc')
        self.assertEqual(self.dev.getLocationName(), '/Test/Loc')


    def testAddLocation(self):
        self.dev.addLocation('/Test/Loc')
        self.assert_('/Test/Loc' in self.dmd.Locations.getOrganizerNames())


    def testSetHWTag(self):
        self.dev.setHWTag('my test asset tag')
        self.assertEqual(self.dev.getHWTag(), 'my test asset tag')


    def testSetHWSerialNumber(self):
        self.dev.setHWSerialNumber('testSWKey')
        self.assertEqual(self.dev.getHWSerialNumber(), 'testSWKey')


    def testSetOSProductKey(self):
        unicodeificated = 'ab\xefcd'.decode('latin1')
        self.dev.setOSProductKey(unicodeificated)
        self.assertEqual(self.dev.getOSProductKey(), u'ab\xefcd')


    def testSetOSProductKeyViaEditDevice(self):
        self.dev.manage_editDevice(osManufacturer='Apple',
                                   osProductName='Macos 10.4.1')
        self.assertEqual(self.dev.getOSProductKey(), 'Darwin 8.1.0')


    def testSetHWProductKey(self):
        self.dev.setHWProductKey('testHWKey')
        self.assertEqual(self.dev.getHWProductKey(), 'testHWKey')


    def testSetHWProductKeyViaEditDevice(self):
        self.dev.manage_editDevice(hwManufacturer='HP',
                                   hwProductName='ProLiant 800')
        self.assertEqual(self.dev.getHWProductKey(), 'ProLiant 800')


    def testSetLastChange(self):
        dt = DateTime()
        self.dev.setLastChange(dt)
        self.assertEqual(self.dev.getLastChange(), dt)


    def testSetSnmpLastCollection(self):
        dt = DateTime()
        self.dev.setSnmpLastCollection(dt)
        self.assertEqual(self.dev.getSnmpLastCollection(), dt)


    def testSetHWProduct(self):
        self.dev.setHWProduct('testHW', 'HP')
        self.assert_('testHW' in self.dev.getDmdRoot("Manufacturers")\
                     .getProductNames('HP')\
                    )


    def testSetLastPollSnmpUpTime(self):
        dt = DateTime()
        self.dev.setLastPollSnmpUpTime(dt)
        self.assertEqual(int(dt), self.dev.getLastPollSnmpUpTime())


    def testSetOSProduct(self):
        self.dev.setOSProduct('testOS', 'HP')
        self.assert_('testOS' in self.dev.getDmdRoot("Manufacturers")\
                     .getProductNames('HP')\
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


    def testGetOSProductName(self):
        self.dev.manage_editDevice(osManufacturer='Apple',
                                   osProductName='Macos 10.4.1')
        self.assertEqual(self.dev.getOSProductName(), "Macos 10.4.1")


    def testSnmpAgeCheck(self):
        self.dev.setSnmpLastCollection()
        time.sleep(0.1)  #because computers are too fast...
        self.assertEqual(self.dev.snmpAgeCheck(0), 1)
        self.assertEqual(self.dev.snmpAgeCheck(5), None)


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
        self.assertEqual(self.dev.getPerformanceServerName(), 'perfMon')
        self.dev.setPerformanceMonitor('perfMon', 'nextMon')
        self.assertEqual(self.dev.getPerformanceServerName(), 'nextMon')


    def testSetProdState(self):
        self.dev.setProdState(500)
        self.assertEqual(self.dev.getProductionStateString(), 'Pre-Production')


    def testMonitorDevice(self):
        self.dev.setProdState(1000)
        self.assert_(self.dev.monitorDevice())
        self.dev.setProdState(-1)
        self.assert_(not self.dev.monitorDevice())

    def test_zPythonClass(self):
        self.dmd.Devices.zPythonClass = \
                "Products.ZenModel.tests.ClassTestDevice"
        d = self.dmd.Devices.createInstance('testingclass')
        # Import the long way so isinstance recognizes they're the same
        from Products.ZenModel.tests.ClassTestDevice import ClassTestDevice
        self.assert_(isinstance(d, ClassTestDevice))

    def testSetManageIp(self):
        testIp = '1.2.3.4'
        self.dev.setManageIp(testIp)
        self.assertEqual(self.dev.getManageIp(), testIp)

        # Need a network interface to register an IP in catalog
        from Products.ZenModel.IpInterface import IpInterface
        tmpIface = IpInterface('testNIC')
        self.dev.os.interfaces._setObject('testNIC', tmpIface)
        self.iface1 = self.dev.getDeviceComponents()[0]
        self.iface1.addIpAddress('1.2.3.4')

        ip = self.dev.getNetworkRoot().findIp(testIp)
        self.assert_(ip is not None)

        self.dev.setManageIp(testIp)

        # What about duplicates?
        d = self.dmd.Devices.createInstance('localhost')
        d.setManageIp()
        self.assertTrue(d.getManageIp() in ('127.0.0.1', '::1'))

        # Mask out the warning
        log = logging.getLogger()
        curLogLevel = log.getEffectiveLevel()
        log.setLevel(logging.ERROR)
        d.setManageIp(testIp)
        log.setLevel(curLogLevel)
        self.assertTrue(d.getManageIp() in ('127.0.0.1', '::1'))

    def testManage_editDevice(self):
        self.dev.manage_editDevice()

        self.assertEqual(self.dev.hw.tag, '')
        self.assertEqual(self.dev.hw.serialNumber, '')
        self.assertEqual(self.dev.zSnmpCommunity, self.dmd.Devices.zSnmpCommunity)
        self.assertEqual(self.dev.zSnmpPort, 161)
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.manage_editDevice(tag='tag', serialNumber='SN123',
                        zSnmpCommunity='theHood', zSnmpPort=121, zSnmpVer='v2',
                        rackSlot='1', productionState=1000,
                        comments="cross your fingers", hwManufacturer="HP",
                        hwProductName="hwProd", osManufacturer="Apple",
                        osProductName="osProd", locationPath='/test/loc',
                        groupPaths=['/group/path1','/group/path2'],
                        systemPaths=['/sys/path1','/sys/path2'],
                        performanceMonitor='perfMon',
                        title='testTitle')

        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, '1')
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "HP")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationLink(), "<a href='/zport/dmd/Locations/test/loc'>/test/loc</a>")
        self.assertEqual(self.dev.getLocationName(), '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames())
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames())
        self.assert_('/sys/path1' in self.dev.getSystemNames())
        self.assert_('/sys/path2' in self.dev.getSystemNames())
        self.assertEqual(self.dev.getPerformanceServerName(), "perfMon")
        self.assertEqual(self.dev.title, "testTitle")


    def testManage_updateDevice(self):
        self.dev.manage_editDevice()

        self.assertEqual(self.dev.hw.tag, '')
        self.assertEqual(self.dev.hw.serialNumber, '')
        self.assertEqual(self.dev.zSnmpCommunity, self.dmd.Devices.zSnmpCommunity)
        self.assertEqual(self.dev.zSnmpPort, 161)
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(tag='tag') # set value
        self.assertEqual(self.dev.hw.tag, 'tag') #verify change
        self.assertEqual(self.dev.hw.serialNumber, '')
        self.assertEqual(self.dev.zSnmpCommunity, self.dmd.Devices.zSnmpCommunity)
        self.assertEqual(self.dev.zSnmpPort, 161)
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(serialNumber='SN123') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')  # verify change
        self.assertEqual(self.dev.zSnmpCommunity, self.dmd.Devices.zSnmpCommunity)
        self.assertEqual(self.dev.zSnmpPort, 161)
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(zSnmpCommunity='theHood') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')   # verify change
        self.assertEqual(self.dev.zSnmpPort, 161)
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(zSnmpPort=121) # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121) # verify change
        self.assertEqual(self.dev.zSnmpVer, self.dmd.Devices.zSnmpVer)
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(zSnmpVer='v2') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2') # verify change
        self.assertEqual(self.dev.rackSlot, "")
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(rackSlot='1') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1") # verify change
        self.assertEqual(self.dev.productionState, 1000)
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(productionState=400) # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400) # verify change
        self.assertEqual(self.dev.comments, "")
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(comments="cross your fingers") # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers") # verify change
        self.assertEqual(self.dev.getHWManufacturerName(), "")
        self.assertEqual(self.dev.getHWProductName(), "")
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')


        self.dev.updateDevice(hwProductName="hwProd",
                                     hwManufacturer="hwMan") # set values
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan") # verify change
        self.assertEqual(self.dev.getHWProductName(), "hwProd") # verify change
        self.assertEqual(self.dev.getOSManufacturerName(), "")
        self.assertEqual(self.dev.getOSProductName(), "")
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(osManufacturer="Apple",
                                     osProductName="osProd") # set values
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple") # verify change
        self.assertEqual(self.dev.getOSProductName(), "osProd")  # verify change
        self.assertEqual(self.dev.getLocationLink(), "None")
        self.assertEqual(self.dev.getLocationName(), "")
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(locationPath='/test/loc') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationName(), '/test/loc') # test value
        self.assertEqual(self.dev.getDeviceGroupNames(), [])
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(groupPaths=['/group/path1','/group/path2']) # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationName(), '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames()) # test value
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames()) # test value
        self.assertEqual(self.dev.getSystemNames(), [])
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(systemPaths=['/sys/path1','/sys/path2']) # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationName(), '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames())
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames())
        self.assert_('/sys/path1' in self.dev.getSystemNames()) # test value
        self.assert_('/sys/path2' in self.dev.getSystemNames()) # test value
        self.assertEqual(self.dev.getPerformanceServerName(), "localhost")
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(performanceMonitor='perfMon') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationName(), '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames())
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames())
        self.assert_('/sys/path1' in self.dev.getSystemNames())
        self.assert_('/sys/path2' in self.dev.getSystemNames())
        self.assertEqual(self.dev.getPerformanceServerName(), "perfMon") # test value
        self.assertEqual(self.dev.title, '')

        self.dev.updateDevice(title='testTitle') # set value
        self.assertEqual(self.dev.hw.tag, 'tag')
        self.assertEqual(self.dev.hw.serialNumber, 'SN123')
        self.assertEqual(self.dev.zSnmpCommunity, 'theHood')
        self.assertEqual(self.dev.zSnmpPort, 121)
        self.assertEqual(self.dev.zSnmpVer, 'v2')
        self.assertEqual(self.dev.rackSlot, "1")
        self.assertEqual(self.dev.productionState, 400)
        self.assertEqual(self.dev.comments, "cross your fingers")
        self.assertEqual(self.dev.getHWManufacturerName(), "hwMan")
        self.assertEqual(self.dev.getHWProductName(), "hwProd")
        self.assertEqual(self.dev.getOSManufacturerName(), "Apple")
        self.assertEqual(self.dev.getOSProductName(), "osProd")
        self.assertEqual(self.dev.getLocationName(), '/test/loc')
        self.assert_('/group/path1' in self.dev.getDeviceGroupNames())
        self.assert_('/group/path2' in self.dev.getDeviceGroupNames())
        self.assert_('/sys/path1' in self.dev.getSystemNames())
        self.assert_('/sys/path2' in self.dev.getSystemNames())
        self.assertEqual(self.dev.getPerformanceServerName(), "perfMon")
        self.assertEqual(self.dev.title, "testTitle") # test value

        # we should not set title to None
        self.dev.updateDevice(title=None) # set value
        self.assertEqual(self.dev.title, "testTitle") # test value


    def test_setZProperties(self):
        decoding = self.dmd.Devices.zCollectorDecoding
        zProperties = {'zCommandUsername':'testuser',
                       'zCollectorDecoding':decoding}
        device = BaseDeviceLoader(self.dmd).load_device(
                    'testdevice', '/', 'none', 'localhost',
                    '1.1.1.1', zProperties=zProperties)
        self.assert_(device is not None)
        self.assertEqual(device.zCommandUsername, 'testuser')
        self.assertEqual(device.zCollectorDecoding, decoding)
        self.assertEqual(device.isLocal('zCommandUsername'), True)
        self.assertEqual(device.isLocal('zCollectorDecoding'), False)

    def testSnmpLastCollectionString(self):
        """
        When a device has not been modeled make sure we are not
        showing an invalid date
        """
        dev = self.dmd.Devices.createInstance('testsnmpcollection')
        lastcollection = dev.getSnmpLastCollectionString()
        self.assertEqual(lastcollection, "Not Modeled")

    def testPrettyLinkWithTitleOrId(self):
        dev = manage_createDevice(self.dmd, 'testId', '/')
        link = dev.getPrettyLink()
        self.assert_( link.endswith( 'testId</a>' ) )
        dev.title = 'testTitle'
        link = dev.getPrettyLink()
        self.assert_( link.endswith( 'testTitle</a>' ) )

    def testRenameDeviceDuplicateName(self):
        testId1 = 'testId1'
        testId2 = 'testId2'
        dev1 = manage_createDevice(self.dmd, testId1, '/')
        manage_createDevice(self.dmd, testId2, '/Devices')
        self.assertRaises( DeviceExistsError,
                           dev1.renameDevice,
                           testId2 )

class GetSnmpConnInfoTest(ZenModelBaseTest):

    def runTest(self):
        from Products.ZenModel.Device import manage_addDevice
        from Products.ZenHub.services.PerformanceConfig import ATTRIBUTES
        devices = self.dmd.findChild('Devices')
        manage_addDevice(devices, 'test')
        device = devices.findChild('test')
        info = device.getSnmpConnInfo()
        for attribute in ATTRIBUTES:
            self.assertEqual(getattr(device, attribute, None),
                             getattr(info, attribute, None))

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDevice))
    suite.addTest(makeSuite(GetSnmpConnInfoTest))
    return suite

if __name__=="__main__":
    framework()
