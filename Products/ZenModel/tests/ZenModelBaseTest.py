#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################
import unittest

from Testing import ZopeTestCase
from Testing.ZopeTestCase import ZopeTestCase as BaseTestCase

from Products.ZenModel.DmdBuilder import DmdBuilder

from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenEvents.MySqlSendEvent import MySqlSendEventMixin
from Products.ZenEvents import MySqlEventManager

from Products.ZenModel.System import System
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenModel.Location import Location
from Products.ZenModel.IpNetwork import IpNetwork
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenModel.ZentinelPortal import PortalGenerator
from Products.ZenModel.ManufacturerRoot import ManufacturerRoot


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


class DummyCursor(object):
    def __init__(self, *args, **kwds): pass
    def execute(self, *args, **kwds): pass


class DummyConnection(object):
    def __init__(self, *args, **kwds): pass
    def cursor(self):
        return DummyCursor()
    def close(self): pass


class DummyManager(MySqlSendEventMixin, EventManagerBase):
    def __init__(self, *args, **kwds):
        EventManagerBase.__init__(self, *args, **kwds)
    def connect(self, *args, **kwds): return DummyConnection()
    def sendEvent(self, *args, **kwds): pass
    def sendEvents(self, *args, **kwds): pass
    def doSendEvent(self, *args, **kwds): pass
    def getEventSummary(self, *args, **kwds): pass
    def getEventDetail(self, *args, **kwds): pass
    def getGenericStatus(self, *args, **kwds): pass
    def getOrganizerStatus(self, *args, **kwds): pass
    def getOrganizerStatusIssues(self, *args, **kwds): pass
    def getDeviceIssues(self, *args, **kwds): pass
    def getDeviceStatus(self, *args, **kwds): pass
    def getHeartbeat(self, *args, **kwds): pass
    def getComponentStatus(self, *args, **kwds): pass
    def getEventList(self, *args, **kwds): return []
    def applyEventContext(self, evt): return evt
    def applyDeviceContext(self, dev, evt): return evt


def manage_addDummyManager(context, id):
    context._delObject(id)
    context._setObject(id, DummyManager(id))
    evtmgr = context._getOb(id)
    evtmgr.installIntoPortal()


class Builder(DmdBuilder):

    def build(self):
        DmdBuilder.build(self)
        manage_addDummyManager(self.dmd, 'ZenEventManager')
        manage_addDummyManager(self.dmd, 'ZenEventHistory')


class ZenModelBaseTest(BaseTestCase):


    def setUp(self):
        """setup schema manager and add needed permissions"""
        BaseTestCase.setUp(self)
        gen = PortalGenerator()
        gen.create(self.app, 'zport', True)
        builder = Builder(self.app.zport, 'dbuser', 'dbpass', 'dbtable')
        builder.build()
        self.dmd = builder.dmd


    def tearDown(self):
        self.app = None
        self.dmd = None


    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst
