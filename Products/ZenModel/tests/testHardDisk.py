#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.HardDisk import HardDisk

from ZenModelBaseTest import ZenModelBaseTest

class TestHardDisk(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = HardDisk('hdd')
        self.dev.hw.harddisks._setObject('hdd',tmpo)
        self.hdd = self.dev.hw.harddisks()[0]


    def testSetManageIp(self):
        self.hdd.setManageIp('1.2.3.4/24')
        self.assert_(self.hdd.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.hdd.getManageIp() == '2.3.4.5/24')
        

    def testGets(self):
        self.assert_(self.hdd.getInstDescription() == 'hdd')
        self.assert_(self.hdd.name() == 'hdd')
        self.assert_(self.hdd.hostname() == 'testdev')
        self.assert_(self.hdd.getParentDeviceName() == 'testdev')
        import pdb;pdb.set_trace()
        self.assert_(self.hdd.getParentDeviceUrl() == 'zport/dmd/Devices/devices/testdev')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestHardDisk))
    return suite

if __name__=="__main__":
    framework()
