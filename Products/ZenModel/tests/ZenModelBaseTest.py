#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import unittest

from Testing import ZopeTestCase
from Testing.ZopeTestCase import ZopeTestCase as BaseTestCase

from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ZentinelPortal import PortalGenerator


ZopeTestCase.installProduct('ZenRelations', 1)
ZopeTestCase.installProduct('ZenModel', 1)
ZopeTestCase.installProduct('ZCatalog', 1)
ZopeTestCase.installProduct('OFolder', 1)
ZopeTestCase.installProduct('ManagableIndex', 1)
ZopeTestCase.installProduct('AdvancedQuery', 1)
ZopeTestCase.installProduct('ZCTextIndex', 1)
ZopeTestCase.installProduct('CMFCore', 1)
ZopeTestCase.installProduct('CMFDefault', 1)
ZopeTestCase.installProduct('MailHost', 1)
ZopeTestCase.installProduct('Transience', 1)


class ZenModelBaseTest(BaseTestCase):

    #def afterSetUp(self):
    def setUp(self):
        """setup schema manager and add needed permissions"""
        BaseTestCase.setUp(self)
        gen = PortalGenerator()
        gen.create(self.app, 'zport', True)
        self.dmd = self.create(self.app.zport, DataRoot, "dmd")
        self.app.zport.zPrimaryBasePath = ("",)
        dev = DeviceClass('Devices')
        self.dmd._setObject(dev.getId(), dev)
        self.dmd.Devices.createCatalog()
        net = IpNetwork('Networks')
        self.dmd._setObject(net.getId(), net)
        self.dmd.Networks.createCatalog()
        group = DeviceGroup('Groups')
        self.dmd._setObject(group.getId(), group)
        mon = MonitorClass('Monitors')
        self.dmd._setObject(mon.getId(), mon)

    def tearDown(self):
        self.app = None
        self.dmd = None


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst
