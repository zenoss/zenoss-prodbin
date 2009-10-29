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

import transaction

import zope.component
from zope.traversing.adapters import DefaultTraversable

from Testing import ZopeTestCase
from Testing.ZopeTestCase.ZopeTestCase import standard_permissions
from Testing.ZopeTestCase.layer import ZopeLite
if 0:
    standard_permissions = None         # pyflakes

from Products.Five import zcml

from Products.ZenModel.DmdBuilder import DmdBuilder
from Products.ZenModel.ZentinelPortal import PortalGenerator
from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenEvents.MySqlSendEvent import MySqlSendEventMixin
from Products.ZenRelations.ZenPropertyManager import setDescriptors
from Products.ZenEvents.MySqlEventManager import log
from Products.ZenUtils.Utils import unused
from zope.testing.cleanup import cleanUp

log.warn = lambda *args, **kwds: None

# setup the Products needed for the Zenoss test instance
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
ZopeTestCase.installProduct('ZenRelations', 1)


def manage_addDummyManager(context, id):
    context._delObject(id)
    context._setObject(id, DummyManager(id))
    evtmgr = context._getOb(id)
    evtmgr.installIntoPortal()


class DummyCursor(object):
    def __init__(self, *args, **kwds): pass
    def execute(self, *args, **kwds): pass


class DummyConnection(object):
    def __init__(self, *args, **kwds): pass
    def cursor(self):
        return DummyCursor()
    def close(self): pass


class DummyManager(MySqlSendEventMixin, EventManagerBase):
    __pychecker__ = 'no-override'
    def __init__(self, *args, **kwds):
        EventManagerBase.__init__(self, *args, **kwds)
    def connect(self, *args, **kwds):
        unused(args, kwds)
        return DummyConnection()
    def sendEvent(self, *args, **kwds): unused(args, kwds)
    def sendEvents(self, *args, **kwds): unused(args, kwds)
    def doSendEvent(self, *args, **kwds): unused(args, kwds)
    def getEventSummary(self, *args, **kwds): unused(args, kwds)
    def getEventDetail(self, *args, **kwds): unused(args, kwds)
    def getGenericStatus(self, *args, **kwds): unused(args, kwds)
    def getOrganizerStatus(self, *args, **kwds): unused(args, kwds)
    def getOrganizerStatusIssues(self, *args, **kwds): unused(args, kwds)
    def getDeviceIssues(self, *args, **kwds): unused(args, kwds)
    def getDeviceStatus(self, *args, **kwds): unused(args, kwds)
    def getHeartbeat(self, *args, **kwds): unused(args, kwds)
    def getComponentStatus(self, *args, **kwds): unused(args, kwds)
    def getEventList(self, *args, **kwds): unused(args, kwds); return []
    def applyEventContext(self, evt): return evt
    def applyDeviceContext(self, dev, evt): unused(dev); return evt


class Builder(DmdBuilder):

    def build(self):
        DmdBuilder.build(self)
        #manage_addDummyManager(self.dmd, 'ZenEventManager')
        #manage_addDummyManager(self.dmd, 'ZenEventHistory')



class ZenossTestCaseLayer(ZopeLite):

    @classmethod
    def setUp(cls):
        import Products

        zope.component.testing.setUp(cls)
        zope.component.provideAdapter(DefaultTraversable, (None,))
        zcml.load_config('testing.zcml', Products.ZenTestCase)

    @classmethod
    def tearDown(cls):
        cleanUp()


class BaseTestCase(ZopeTestCase.ZopeTestCase):

    layer = ZenossTestCaseLayer

    def afterSetUp(self):
        gen = PortalGenerator()
        if hasattr( self.app, 'zport' ):
            self.app._delObject( 'zport' )
        gen.create(self.app, 'zport', True)
        # builder params:
        # portal, cvthost, evtuser, evtpass, evtdb,
        #    smtphost, smtpport, pagecommand
        builder = DmdBuilder(self.app.zport, 'localhost', 'zenoss', 'zenoss',
                            'events', 3306, 'localhost', '25', 
                             '$ZENHOME/bin/zensnpp localhost 444 $RECIPIENT')
        builder.build()
        self.dmd = builder.dmd

        self.dmd.ZenUsers.manage_addUser('tester', roles=('Manager',))
        user = self.app.zport.acl_users.getUserById('tester')
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, user)

        # Let's hide transaction.commit() so that tests don't fubar
        # each other
        self._transaction_commit=transaction.commit
        transaction.commit=lambda *x: None

        setDescriptors(self.dmd.propertyTransformers)


    def tearDown(self):
        if hasattr( self, '_transaction_commit' ):
            transaction.commit=self._transaction_commit
        self.app = None
        self.dmd = None
        super(BaseTestCase, self).tearDown()

    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst

