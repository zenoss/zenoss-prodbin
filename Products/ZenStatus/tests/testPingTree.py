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

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.ZenModel.IpInterface import IpInterface
from Products.ZenModel.IpRouteEntry import IpRouteEntry

from Products.ZenHub.services.PingConfig import PingConfig

class TestPingTree(BaseTestCase):

    def addInterface(self, dev, addr):
        count = len(dev.os.interfaces())
        name = 'iface%d' % count
        tmpo = IpInterface(name)
        dev.os.interfaces._setObject(name, tmpo)
        tmpo = dev.os.interfaces._getOb(name)
        tmpo.setIpAddresses(addr)
        tmpo.ifindex = count
        tmpo.interfaceName = name
        return tmpo


    def makeDevice(self, hostname, ip):
        dev = self.dmd.Devices.createInstance(hostname)
        dev.manageIp = ip
        self.addInterface(dev, ip + '/24')
        return dev
        

    def setUp(self):
        BaseTestCase.setUp(self)
        self.dev = self.makeDevice('testdev', '1.2.3.4')
        self.iface1 = self.addInterface(self.dev, '2.3.4.5/24')
        
        tmpdev = self.makeDevice('testdev2', '1.2.3.5')

        tmpo = IpRouteEntry('rEntry')
        self.dev.os.routes._setObject('rEntry',tmpo)
        self.rEntry = self.dev.os.routes()[0]


        tempdev = self.makeDevice('testdev3', '3.4.5.6')
        self.rEntry.setNextHopIp('3.4.5.6')

        for d in self.dmd.Devices.devices():
            d.setPerformanceMonitor('localhost')

    def testPingTree(self):
        self.assert_(self.rEntry.getNextHopIp() == '3.4.5.6')
        pc = PingConfig(self.dmd, 'localhost')
        nodes = pc.remote_getPingTree('testdev', '1.2.3.4')
        assert nodes
        pjs = list(nodes.pjgen())
        assert len(pjs) == 3
        assert [x.hostname for x in pjs] == ['testdev', 'testdev3', 'testdev2']

        tempdev = self.makeDevice('testdev4', '3.4.5.7')
        tempdev.setPerformanceMonitor('localhost')
        
        nodes = pc.remote_getPingTree('testdev', '1.2.3.4')
        pjs = list(nodes.pjgen())
        assert [x.hostname for x in pjs] == [
            'testdev', 'testdev3', 'testdev4', 'testdev2']

        tempdev = self.makeDevice('testdev5', '1.2.3.6')
        tempdev.setPerformanceMonitor('localhost')
        nodes = pc.remote_getPingTree('testdev', '1.2.3.4')
        pjs = list(nodes.pjgen())
        assert [x.hostname for x in pjs] == [
            'testdev', 'testdev3', 'testdev4', 'testdev2', 'testdev5']

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPingTree))
    return suite
