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
        self.dev.setOSProductKey('testKey')
        self.assert_(self.dev.getOSProductKey() == 'testKey')


    def testSetHWProductKey(self):
        self.dev.setHWProductKey('testKey')
        self.assert_(self.dev.getHWProductKey() == 'testKey')


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
        self.dev.addManufacturer('testHWMfr')
        self.assert_('testHWMfr' in self.dev.getDmdRoot("Manufacturers").getManufacturerNames())


    def testGetOsVersion(self):
        self.assert_(self.dev.getOsVersion() == "GET_OS_VERSION_HERE")


    def testGetOSProductName(self):
        self.assert_(self.dev.getOSProductName() == "GET_OS_PRODUCT_NAME_HERE")
        

    def testSnmpAgeCheck(self):
        self.dev.setSnmpLastCollection()
        self.assert_(self.dev.snmpAgeCheck(0) == 1)
        self.assert_(self.dev.snmpAgeCheck(5) == None)


    def testSetTerminalServer(self):
        self.dev.setTerminalServer('iDontExist')
        

def main():
       unittest.TextTestRunner().run(test_suite())

if __name__=="__main__":
       unittest.main()
