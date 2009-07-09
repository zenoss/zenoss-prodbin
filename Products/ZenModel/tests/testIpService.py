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

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpService import IpService
from Products.ZenModel.IpInterface import IpInterface

from ZenModelBaseTest import ZenModelBaseTest


class TestIpService(ZenModelBaseTest):

    def setUp(self):
        ZenModelBaseTest.setUp(self)

        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = IpService('ipsvc')
        self.dev.os.ipservices._setObject('ipsvc',tmpo)
        self.ipsvc = self.dev.os.ipservices()[0]


    def testSetIpService(self):
        self.ipsvc.port = 121 #for now, so that setIpService is actually useful
        self.ipsvc.protocol = 'tcp' #ditto
        self.ipsvc.setServiceClass({'protocol':'tcp','port':121})
        self.assert_(self.ipsvc.getProtocol() == 'tcp')
        self.assert_(self.ipsvc.getPort() == 121)
        self.assert_(self.ipsvc.getServiceClass()['protocol'] == 'tcp')
        self.assert_(self.ipsvc.getServiceClass()['port'] == 121)
        self.assert_(self.ipsvc.getKeyword() == self.ipsvc.serviceclass().name)
        self.assert_(self.ipsvc.getDescription() == self.ipsvc.serviceclass().description)
        self.assert_(self.ipsvc.primarySortKey() == 'tcp-00121')
        self.assert_(self.ipsvc.getInstDescription() == 'tcp-121 ips:')
        self.assert_(self.ipsvc.hostname() == 'testdev')


    def testSetManageIp(self):
        tmpo = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[1]
        self.iface.addIpAddress('1.2.3.4')

        # Explicitly set the manageIp at the device level
        self.dev.setManageIp('1.2.3.4/24')
        self.assertEquals(self.dev.getManageIp(), '1.2.3.4/24')
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')

        self.dev.setManageIp('2.3.4.5/24')
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')

        # Explicitly set the manageIp at the service level
        self.ipsvc.ipaddresses = [ '0.0.0.0' ]
        self.ipsvc.setManageIp('1.2.3.4/24')
        self.assertEquals(self.dev.getManageIp(), '2.3.4.5/24')
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')

        # Unset the manageIp
        self.ipsvc.unsetManageIp()
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')

        # Set the manageIp with garbage
        self.ipsvc.setManageIp('HelloWorld')
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')


    def testGetIpAddresses(self):
        # No interfaces defined
        self.assertEquals(self.ipsvc.getNonLoopbackIpAddresses(), [])

        # Have one IP address
        tmpo = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[1]
        self.iface.addIpAddress('1.2.3.4')
        self.dev.setManageIp('1.2.3.4/24')

        self.assertEquals(self.ipsvc.getNonLoopbackIpAddresses(), ['1.2.3.4'])

        # Have two IP addresses
        tmpo = IpInterface('test1')
        self.dev.os.interfaces._setObject('test1',tmpo)
        self.iface1 = self.dev.getDeviceComponents()[2]
        self.iface1.addIpAddress('2.3.4.5')
        self.assertEquals(self.ipsvc.getNonLoopbackIpAddresses(),
              ['1.2.3.4', '2.3.4.5'])
        self.assertEquals(self.ipsvc.getNonLoopbackIpAddresses(showNetMask=True),
              ['1.2.3.4/24', '2.3.4.5/24'])

    def testGetManageIpMultipleInterfaces(self):
        """
        What should happen if multiple interfaces are available for a
        service?  What if you want to select an alternate one?
        """
        # No interfaces defined
        self.assertEquals(self.dev.getManageIp(), '')
        self.assertEquals(self.ipsvc.getManageIp(), '')

        # Have one IP address
        tmpo = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[1]
        self.iface.addIpAddress('1.2.3.4')
        self.dev.setManageIp('1.2.3.4/24')
        self.ipsvc.ipaddresses = [ '0.0.0.0' ]

        self.assertEquals(self.dev.getManageIp(), '1.2.3.4/24')
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')

        # Have two IP addresses
        tmpo = IpInterface('test1')
        self.dev.os.interfaces._setObject('test1',tmpo)
        self.iface1 = self.dev.getDeviceComponents()[2]
        self.iface1.addIpAddress('2.3.4.5')
        self.dev.setManageIp('2.3.4.5/24')

        self.assertEquals(self.dev.getManageIp(), '2.3.4.5/24')
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')

        self.ipsvc.setManageIp('1.2.3.4/24')
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')

        self.ipsvc.unsetManageIp()
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')

        # Restrict the service to only one IP address
        # Happens when a service restarts with new configuration
        self.ipsvc.setManageIp('2.3.4.5/24')
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')
        self.ipsvc.ipaddresses = [ '1.2.3.4' ]
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')

        # Remove an IP address from an interface
        self.ipsvc.ipaddresses = [ '0.0.0.0' ]
        self.ipsvc.setManageIp('1.2.3.4/24')
        self.assertEquals(self.ipsvc.getManageIp(), '1.2.3.4')
        self.iface.setIpAddresses(['10.20.30.40/8'])
        self.assertEquals(self.ipsvc.getManageIp(), '2.3.4.5')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpService))
    return suite

if __name__=="__main__":
    framework()
