###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import logging

from Products.ZenModel.IpInterface import IpInterface

from ZenModelBaseTest import ZenModelBaseTest


log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None


class TestIpAddress(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpIface = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpIface)
        self.iface = self.dev.getDeviceComponents()[0]
        self.iface.addIpAddress('1.2.3.4')
        self.addr = self.iface.getIpAddressObj()


    def testGets(self):#most/all of the get method tests
        self.assert_(self.addr.getIp() == '1.2.3.4')
        self.assert_(self.addr.getIpAddress() == '1.2.3.4/24')
        self.assert_(self.addr.getInterfaceName() == self.addr.interface().name())
        self.assert_(self.addr.getDeviceUrl() == '/zport/dmd/Devices/devices/testdev')
        self.assert_(self.addr.device() == self.dev)
    
    
    def testSetNetmask(self):
        self.addr.setNetmask(8)
        self.assert_(self.addr.getIpAddress() == '1.2.3.4/8')


#    def testSetIpAddress(self):
#        self.addr.setIpAddress('2.3.4.5/16')
#        self.assert_(self.addr.getIpAddress() == '2.3.4.5/16')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpAddress))
    return suite

