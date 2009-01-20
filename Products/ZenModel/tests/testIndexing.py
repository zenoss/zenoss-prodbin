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
    framework = None
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.IpInterface import manage_addIpInterface
from Products.ZenModel.WinService import manage_addWinService
from Products.ZenUtils.FakeRequest import FakeRequest

LOCATION = '/TestLoc/MyLocation'
GROUP    = '/TestGrp/MyGroup'
SYSTEM   = '/TestSys/MySystem'
DEVCLASS = '/TestOrg/MyClass'
OTHERDEVCLASS = '/TestOrg/MyOtherClass'

MAC = '00:11:22:33:44:55'
IPADDR = '10.1.2.3/24'
NET = '10.1.2.0'

class TestPathIndexing(ZenModelBaseTest):

    def setUp(self):
        super(TestPathIndexing,self).setUp()
        self.devcat = self.dmd.Devices.deviceSearch

        self.devclass = self.dmd.Devices.createOrganizer(DEVCLASS)
        self.loc = self.dmd.Locations.createOrganizer(LOCATION)
        self.grp = self.dmd.Groups.createOrganizer(GROUP)
        self.sys = self.dmd.Systems.createOrganizer(SYSTEM)

        # Control
        dummydev =  self.dmd.Devices.createInstance('dummydev')

        self.dev = self.devclass.createInstance('testdev')
        self.dev.setLocation(LOCATION)
        self.dev.setGroups((GROUP,))
        self.dev.setSystems((SYSTEM,))

    def testDeviceIndexOnCreation(self):
        for org in (self.loc, self.grp, self.sys, self.devclass):
            brains = self.devcat(path='/'.join(org.getPrimaryPath()))
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].id, self.dev.id)
            self.assertEqual(brains[0].getObject(), self.dev)

    def testDeviceUnindexOnRemoval(self):
        self.dev.setLocation('')
        self.dev.setGroups([])
        self.dev.setSystems([])

        for org in (self.loc, self.grp, self.sys):
            brains = self.devcat(path='/'.join(org.getPrimaryPath()))
            self.assertEqual(len(brains), 0)

        self.dev.deleteDevice()
        brains = self.devcat(path='/'.join(self.devclass.getPrimaryPath()))
        self.assertEqual(len(brains), 0)

    def testDeviceReindexOnMove(self):
        neworg = self.dmd.Devices.createOrganizer(DEVCLASS+'NEW')
        self.dmd.Devices.moveDevices(DEVCLASS+'NEW', self.dev.id)
        brains = self.devcat(path='/'.join(neworg.getPrimaryPath()))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newloc = self.dmd.Locations.createOrganizer(LOCATION+'NEW')
        self.dev.setLocation(LOCATION+'NEW')
        brains = self.devcat(path='/'.join(newloc.getPrimaryPath()))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newgrp = self.dmd.Groups.createOrganizer(GROUP+'NEW')
        self.dev.setGroups((GROUP+'NEW',))
        brains = self.devcat(path='/'.join(newgrp.getPrimaryPath()))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newsys = self.dmd.Systems.createOrganizer(SYSTEM + 'NEW')
        self.dev.setSystems((SYSTEM+'NEW',))
        brains = self.devcat(path='/'.join(newsys.getPrimaryPath()))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)


class TestComponentIndexing(ZenModelBaseTest):

    def setUp(self):
        super(TestComponentIndexing,self).setUp()
        self.devcat = self.dmd.Devices.deviceSearch
        self.layer2cat = self.dmd.ZenLinkManager._getCatalog(layer=2)
        self.layer3cat = self.dmd.ZenLinkManager._getCatalog(layer=3)

        self.devclass = self.dmd.Devices.createOrganizer(DEVCLASS)
        self.devclass2 = self.dmd.Devices.createOrganizer(DEVCLASS)

        # Control
        dummydev =  self.dmd.Devices.createInstance('dummydev')

        self.dev = self.devclass.createInstance('testdev')

        manage_addIpInterface(self.dev.os.interfaces, 'eth0', True)
        self.iface = self.dev.os.interfaces._getOb('eth0')
        self.iface._setPropValue('macaddress', MAC)
        self.iface.addIpAddress(IPADDR)
        self.ipaddress = self.iface.ipaddresses()[0]
        self.net = self.dmd.Networks.getNet(NET)
        
        manage_addWinService(self.dev.os.winservices,'wuauserv','test service')
        self.winService = self.dev.os.winservices._getOb('wuauserv')

    def _checkEverything(self):
        for searchcriterion in (dict(macaddress=MAC),
                                dict(deviceId='/'.join(self.dev.getPrimaryPath())),
                                dict(interfaceId=self.iface.getPrimaryId())):
            brains = self.layer2cat(**searchcriterion)
            self.assertEqual(len(brains), 1)
            brain = brains[0]
            self.assertEqual(brain.deviceId, '/'.join(self.dev.getPrimaryPath()))
            self.assertEqual(brain.interfaceId, self.iface.getPrimaryId())
            self.assertEqual(brain.macaddress, MAC)
            self.assertEqual(brain.lanId, 'None')
            self.assertEqual(brain.getObject(), self.iface)

        for searchcriterion in (dict(deviceId=self.dev.id),
                                dict(interfaceId=self.iface.id),
                                dict(ipAddressId=self.ipaddress.getPrimaryId()),
                                dict(networkId=self.net.getPrimaryId())
                               ):
            brains = self.layer3cat(**searchcriterion)
            self.assertEqual(len(brains), 1)
            brain = brains[0]
            self.assertEqual(brain.deviceId, self.dev.id)
            self.assertEqual(brain.interfaceId, self.iface.id)
            self.assertEqual(brain.ipAddressId, self.ipaddress.getPrimaryId())
            self.assertEqual(brain.networkId, self.net.getPrimaryId())
            self.assertEqual(brain.getObject(), self.ipaddress)

    def testComponentIndexOnCreation(self):
        """
        Ensure that the layerN catalogs are updated when the device is created
        """
        self._checkEverything()

    def testComponentUnindexOnDeviceDeletion(self):
        """
        Ensure that the layerN catalogs are updated when the device is deleted
        """
        self.dev.deleteDevice()

        brains = self.layer2cat(deviceId = self.dev.getPrimaryId())
        self.assertEqual(len(brains), 0)

        brains = self.layer3cat(deviceId = self.dev.id)
        self.assertEqual(len(brains), 0)

    def testComponentReindexOnDeviceMove(self):
        """
        Ensure that the layerN catalogs are updated when the device is moved
        """
        neworg = self.dmd.Devices.createOrganizer(DEVCLASS+'NEW')
        self.dmd.Devices.moveDevices(DEVCLASS+'NEW', self.dev.id)
        self._checkEverything()
        
    def testWinSerivceComponentReindexOnServiceClassZMonitorChange(self):
        """
        Ensure the WinServices in the componentSearch catalog are re-indexed 
        when saveZenProperties is called on the Service Class and zMonitor is 
        changed
        """
        svcClass = self.dmd.Services.WinService.serviceclasses._getOb(self.winService.id)
        
        winSvc = self.dev.getMonitoredComponents(type='WinService')
        #by default monitor is off; should find nothing
        self.assertFalse( winSvc )
        monitored = svcClass.zMonitor
        self.assertFalse( monitored )
        
        #fake request and turn zMonitor to true
        request = FakeRequest()
        request.form = {'zMonitor': True}
        kwargs = {'REQUEST': request}
        svcClass.saveZenProperties(**kwargs)
        
        #verify monitored flag changed and that component is now found
        monitored = svcClass.zMonitor
        self.assertTrue( monitored )
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        self.assertTrue ( winSvc2 )

        #test that changing zProperty directly does not affect catalog
        svcClass.setZenProperty('zMonitor', False)
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        #catalog will find component even though zMonitor is false
        #because index was not updated
        self.assertTrue ( winSvc2 )

    def testWinSerivceComponentReindexOnServiceOrganizerZMonitorChange(self):
        """
        Ensure the WinServices in the componentSearch catalog are re-indexed 
        when saveZenProperties is called on the Service Organizer and zMonitor
        is Changed 
        """

        svcOrg = self.dmd.Services
        winSvc = self.dev.getMonitoredComponents(type='WinService')
        #by default monitor is off; should find nothing
        self.assertFalse( winSvc )
        monitored = svcOrg.zMonitor
        self.assertFalse( monitored )
                
        #fake request and turn zMonitor to true
        request = FakeRequest()
        request.form = {'zMonitor': True}
        kwargs = {'REQUEST': request}
        svcOrg.saveZenProperties(**kwargs)
        
        #verify monitored flag changed and that component is now found
        monitored = svcOrg.zMonitor
        self.assertTrue( monitored )
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        self.assertTrue ( winSvc2 )

        #test that changing zProperty directly does not affect catalog
        svcOrg.setZenProperty('zMonitor', False)
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        #catalog will find component even though zMonitor is false
        #because index was not updated
        self.assertTrue ( winSvc2 )

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPathIndexing))
    suite.addTest(makeSuite(TestComponentIndexing))
    return suite

if __name__=="__main__":
    framework()
