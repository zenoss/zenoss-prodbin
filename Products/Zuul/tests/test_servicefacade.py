###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
from zope.interface.verify import verifyClass
from Products.ZenModel.IpService import IpService
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.ZenModel.Service import Service
from Products.Zuul.interfaces import IInstance

class ServiceFacadeTest(ZuulFacadeTestCase):

    def setUp(self):
        super(ServiceFacadeTest, self).setUp()
        self.facade = Zuul.getFacade('service')

    def test_interfaces(self):
        verifyClass(IInstance, Service)

    def test_getInstances(self):
        device = self.dmd.Devices.createInstance('foo')
        device.os.ipservices._setObject('tcp_00121', IpService('tcp_00121'))
        bar = device.os.ipservices()[0]
        bar.port = 121
        bar.protocol = 'tcp'
        bar.setServiceClass({'protocol':'tcp', 'port':121})
        self.assertEqual(1, len(self.dmd.Services.IpService.serviceclasses()))
        ipServiceClass = self.dmd.Services.IpService.serviceclasses()[0]
        self.assertEqual(1, len(ipServiceClass.instances()))
        uid = '/zport/dmd/Services/IpService/serviceclasses/tcp_00121'
        self.dmd.Devices.reIndex()
        instanceInfos = list(self.facade.getInstances(uid))
        self.assertEqual(1, len(instanceInfos))
        instanceInfo = instanceInfos[0]
        self.assertEqual('foo', instanceInfo.device)
        self.assertEqual('tcp_00121', instanceInfo.name)
        self.assertEqual(False, instanceInfo.monitor)
        self.assertEqual('None', instanceInfo.status)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ServiceFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')

