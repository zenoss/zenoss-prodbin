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
from Products.ZenUtils.Utils import localIpCheck, prepId


from Products.ZenHub.services.PingConfig import PingConfig

class TestPingTree(BaseTestCase):

    def addRoute(self, dev, dest, routemask, nexthopid, interface,
                   routeproto='local', routetype='indirect'):
        # Yes, it's *ALMOST* a complete copy of manage_addIpRouteEntry
        dest = '%s/%s' % (dest, routemask)
        id = prepId(dest)
        d = IpRouteEntry(id)
        dev.os.routes._setObject(id, d)
        d = dev.os.routes._getOb(id)
        d.setTarget(dest)
        d.setNextHopIp(nexthopid)
        d.setInterfaceName(interface)
        d.routeproto = routeproto
        d.routetype = routetype
        d.routemask = routemask

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

    def makeDevice(self, hostname, ip, netmask=24, collector='localhost'):
        dev = self.dmd.Devices.createInstance(hostname)
        dev.manageIp = ip
        self.addInterface(dev, '%s/%s' %(ip, netmask))
        dev.setPerformanceMonitor(collector)
        return dev
        
    def buildTestNetwork(self):
        self.dev = self.makeDevice('testdev', '1.2.3.4')
        self.iface1 = self.addInterface(self.dev, '2.3.4.5/24')
        
        tmpdev = self.makeDevice('testdev2', '1.2.3.5')

        tmpo = IpRouteEntry('rEntry')
        self.dev.os.routes._setObject('rEntry',tmpo)
        self.rEntry = self.dev.os.routes()[0]

        tempdev = self.makeDevice('testdev3', '3.4.5.6')
        self.rEntry.setNextHopIp('3.4.5.6')

    def testPingTree(self):
        self.buildTestNetwork()
        self.assert_(self.rEntry.getNextHopIp() == '3.4.5.6')
        pc = PingConfig(self.dmd, 'localhost')
        nodes = pc.getPingTree(self.dmd, 'testdev', '1.2.3.4')
        assert nodes
        pjs = list(nodes.pjgen())
        assert len(pjs) == 3
        assert [x.hostname for x in pjs] == ['testdev', 'testdev3', 'testdev2']

        tempdev = self.makeDevice('testdev4', '3.4.5.7')
        
        nodes = pc.getPingTree(self.dmd, 'testdev', '1.2.3.4')
        pjs = list(nodes.pjgen())
        assert [x.hostname for x in pjs] == [
            'testdev', 'testdev3', 'testdev4', 'testdev2']

        tempdev = self.makeDevice('testdev5', '1.2.3.6')
        nodes = pc.getPingTree(self.dmd, 'testdev', '1.2.3.4')
        pjs = list(nodes.pjgen())
        assert [x.hostname for x in pjs] == [
            'testdev', 'testdev3', 'testdev4', 'testdev2', 'testdev5']

    def buildRaddleNetwork(self):
        """
        Devices

           (Zenoss collector)
           collector1 = 172.31.10.10 (lives in 172.31.10.0/24)

           dev0 = 172.31.100.10 (lives in 172.31.100.0/28)
           dev1 = 172.31.100.20 (lives in 172.31.100.16/28)
           dev2 = 172.31.100.40 (lives in 172.31.100.32/28)

           router1 
             iface0   172.31.10.1 (lives in 172.31.10.0/24)
             iface1   172.31.100.1  (lives in 172.31.100.0/28)
             iface2   172.31.100.17 (lives in 172.31.100.16/28)
             iface3   172.31.100.33 (lives in 172.31.100.32/28)

        Note that there is no 172.31.100.0/24 network
        """
        collector1 = self.makeDevice('collector1', '172.31.10.10', netmask=24)
        self.addRoute(collector1, dest='0.0.0.0', routemask='0',
                      nexthopid='172.31.10.1', interface='iface0')

        dev0 = self.makeDevice('dev0', '172.31.100.10', netmask=28)
        self.addRoute(dev0, dest='0.0.0.0', routemask='0',
                      nexthopid='172.31.100.1', interface='iface0')

        dev1 = self.makeDevice('dev1', '172.31.100.20', netmask=28)
        self.addRoute(dev1, dest='0.0.0.0', routemask='0',
                      nexthopid='172.31.100.17', interface='iface0')

        dev2 = self.makeDevice('dev2', '172.31.100.40', netmask=28)
        self.addRoute(dev2, dest='0.0.0.0', routemask='0',
                      nexthopid='172.31.100.33', interface='iface0')

        # And now connect them all together
        router1 = self.makeDevice('router1', '172.31.10.1', netmask=24)
        self.addRoute(router1, dest='172.31.10.0', routemask='24',
                      nexthopid='172.31.10.1', interface='iface0',
                      routetype='direct')
        self.addInterface(router1, '172.31.100.1/28')
        self.addRoute(router1, dest='172.31.100.0', routemask='28',
                      nexthopid='172.31.100.1', interface='iface1',
                      routetype='direct')
        self.addInterface(router1, '172.31.100.17/28')
        self.addRoute(router1, dest='172.31.100.16', routemask='28',
                      nexthopid='172.31.100.17', interface='iface2',
                      routetype='direct')
        self.addInterface(router1, '172.31.100.33/28')
        self.addRoute(router1, dest='172.31.100.32', routemask='28',
                      nexthopid='172.31.100.33', interface='iface3', 
                      routetype='direct')

        return [collector1, router1, dev0, dev1, dev2]

    def testRaddle(self):
        [collector1, router1, dev0, dev1, dev2] = self.buildRaddleNetwork()

        # Sanity check the network
        self.assertEqual(collector1.traceRoute('dev0'), ['172.31.10.1', 'dev0'])
        self.assertEqual(collector1.traceRoute('dev1'), ['172.31.10.1', 'dev1'])
        self.assertEqual(collector1.traceRoute('dev2'), ['172.31.10.1', 'dev2'])

        self.assertEqual(dev0.traceRoute('collector1'), ['172.31.100.1', 'collector1'])
        self.assertEqual(dev0.traceRoute('dev1'), ['172.31.100.1', 'dev1'])
        self.assertEqual(dev0.traceRoute('dev2'), ['172.31.100.1', 'dev2'])

        # Set up the ping tree just like zenhub does
        pc = PingConfig(self.dmd, 'localhost')
        pingjobs = pc.getPingTree(self.dmd, 'collector1', '172.31.10.10')

        # Organize the job list
        name2pj = dict([(x.hostname, x) for x in pingjobs.pjgen()])
        routerPj = name2pj.get('router1')
        dev2Pj = name2pj.get('dev2')

        # Make sure everything is sane
        self.assertEqual(routerPj.status, 0)
        self.assertEqual(dev2Pj.checkpath(), None)

        # Oh no! router1 has gone down!
        routerPj.status = 1
        # dev2 reports an issue -- is it the problem or a victim?
        self.assertEqual(dev2Pj.checkpath(), 'router1')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPingTree))
    return suite
