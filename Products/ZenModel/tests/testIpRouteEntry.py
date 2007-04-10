#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import logging

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpInterface import IpInterface
from Products.ZenModel.IpRouteEntry import IpRouteEntry

from ZenModelBaseTest import ZenModelBaseTest

log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None


class TestIpRouteEntry(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)

        self.dev = self.dmd.Devices.createInstance('testdev')

        tmpo = IpInterface('test0')
        self.dev.os.interfaces._setObject('test0',tmpo)
        self.iface0 = self.dev.os.interfaces._getOb('test0')
        self.iface0.setIpAddresses('1.2.3.4/24')
        self.iface0.ifindex = 0
        self.iface0.interfaceName = 'iface0'

        tmpo = IpInterface('test1')
        self.dev.os.interfaces._setObject('test1',tmpo)
        self.iface1 = self.dev.os.interfaces._getOb('test1')
        self.iface1.setIpAddresses('2.3.4.5/24')
        self.iface1.ifindex = 1
        self.iface1.interfaceName = 'iface1'

        tmpo = IpRouteEntry('rEntry')
        self.dev.os.routes._setObject('rEntry',tmpo)
        self.rEntry = self.dev.os.routes()[0]


    def testSetManageIp(self):
        self.rEntry.setManageIp('1.2.3.4/24')
        self.assert_(self.rEntry.getManageIp() == '1.2.3.4/24')
        self.assert_(self.iface0.getManageIp() == '1.2.3.4/24')
        self.assert_(self.iface1.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        

    def testSetNextHopIp(self):
        tempdev = self.dmd.Devices.createInstance('testdev2')
        tmpo = IpInterface('test2')
        tempdev.os.interfaces._setObject('test2',tmpo)
        iface2 = tempdev.os.interfaces()[0]
        iface2.setIpAddresses('3.4.5.6/24')
        self.rEntry.setNextHopIp('3.4.5.6')
        self.assert_(self.rEntry.getNextHopIp() == '3.4.5.6')
        self.assert_(self.rEntry.getNextHopIpLink() == "<a href='/zport/dmd/Networks/3.4.5.0/ipaddresses/3.4.5.6'>3.4.5.6</a>")
        self.assert_(self.rEntry.getNextHopDevice() == tempdev)
        self.assert_(self.rEntry.getNextHopDeviceLink() == "<a href='/zport/dmd/Devices/devices/testdev2/'>testdev2</a>")
        #TODO: test setNextHopIp locally


    def testSetTarget(self):
        self.rEntry.setTarget('1.2.3.0/24')
        self.assert_(self.rEntry.getTarget() == '1.2.3.0/24')
        self.assert_(self.rEntry.matchTarget('1.2.3.0'))
        self.assert_(self.rEntry.getTargetIp() == '1.2.3.0')
        self.assert_(self.rEntry.getTargetLink() == "<a href='/zport/dmd/Networks/1.2.3.0'>1.2.3.0</a>")
        #TODO(?): test setTarget locally


    def testSetInterfaceIndex(self):
        self.rEntry.setInterfaceIndex(0)
        self.assert_(self.rEntry.getInterfaceIndex() == 0)
        self.assert_(self.rEntry.getInterfaceName() == 'test0')
        self.assert_(self.rEntry.getInterfaceName() == 'iface0')
        self.assert_(self.rEntry.getInterfaceIp() == '1.2.3.4')

        self.rEntry.setInterfaceIndex(1)
        self.assert_(self.rEntry.getInterfaceIndex() == 1)
        self.assert_(self.rEntry.getInterfaceName() == 'test1')
        self.assert_(self.rEntry.getInterfaceName() == 'iface1')
        self.assert_(self.rEntry.getInterfaceIp() == '2.3.4.5')


    def testSetInterfaceName(self):
        self.rEntry.setInterfaceName('test0')
        self.assert_(self.rEntry.getInterfaceIndex() == 0)
        self.assert_(self.rEntry.getInterfaceName() == 'test0')
        self.assert_(self.rEntry.getInterfaceName() == 'iface0')
        self.assert_(self.rEntry.getInterfaceIp() == '1.2.3.4')

        self.rEntry.setInterfaceName('test1')
        self.assert_(self.rEntry.getInterfaceIndex() == 1)
        self.assert_(self.rEntry.getInterfaceName() == 'test1')
        self.assert_(self.rEntry.getInterfaceName() == 'iface1')
        self.assert_(self.rEntry.getInterfaceIp() == '2.3.4.5')

        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpRouteEntry))
    return suite

if __name__=="__main__":
    framework()
