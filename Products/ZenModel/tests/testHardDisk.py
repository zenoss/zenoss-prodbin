#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import pdb
import unittest

import Globals
import transaction

from Products.ZenModel.Exceptions import *
from Products.ZenUtils.ZeoConn import ZeoConn
from Products.ZenModel.HardDisk import HardDisk

zeoconn = ZeoConn()

class TestHardDisk(unittest.TestCase):

    def setUp(self):
        self.dmd = zeoconn.dmd
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = HardDisk('hdd')
        self.dev.hw.harddisks._setObject('hdd',tmpo)
        self.hdd = self.dev.hw.harddisks()[0]


    def tearDown(self):
        transaction.abort()
        self.dmd = None
    
        
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
        self.assert_(self.hdd.getParentDeviceUrl() == 'zport/dmd/Devices/devices/testdev')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestHardDisk))
    return suite

if __name__=="__main__":
    framework()
