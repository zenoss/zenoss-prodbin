##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging

import zope.component
from zope.traversing.adapters import DefaultTraversable
from transaction._transaction import Transaction

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
from Products.ZenUtils.Utils import unused, load_config_override
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
    def getDeviceIssues(self, *args, **kwds): unused(args, kwds)
    def getHeartbeat(self, *args, **kwds): unused(args, kwds)
    def getEventList(self, *args, **kwds): unused(args, kwds); return []
    def applyEventContext(self, evt): return evt
    def applyDeviceContext(self, dev, evt): unused(dev); return evt

class ZenossTestCaseLayer(ZopeLite):

    @classmethod
    def testSetUp(cls):
        import Products

        zope.component.testing.setUp(cls)
        zope.component.provideAdapter(DefaultTraversable, (None,))
        zcml.load_config('testing.zcml', Products.ZenTestCase)
        import Products.ZenMessaging.queuemessaging
        load_config_override('nopublisher.zcml', Products.ZenMessaging.queuemessaging)

        # Have to force registering these as they are torn down between tests
        from zenoss.protocols.adapters import registerAdapters
        registerAdapters()

        from twisted.python.runtime import platform
        platform.supportsThreads_orig = platform.supportsThreads
        platform.supportsThreads = lambda : None



    @classmethod
    def testTearDown(cls):
        from twisted.python.runtime import platform
        platform.supportsThreads = platform.supportsThreads_orig
        cleanUp()


class BaseTestCase(ZopeTestCase.ZopeTestCase):

    layer = ZenossTestCaseLayer
    _setup_fixture = 0
    disableLogging = True

    def afterSetUp(self):

        super(BaseTestCase, self).afterSetUp()

        if self.disableLogging:
            logging.disable(logging.CRITICAL)

        gen = PortalGenerator()
        if hasattr( self.app, 'zport' ):
            self.app._delObject( 'zport', suppress_events=True)
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
        self._transaction_commit = Transaction.commit
        Transaction.commit=lambda *x: None

        setDescriptors(self.dmd)


    def beforeTearDown(self):
        if hasattr( self, '_transaction_commit' ):
            Transaction.commit=self._transaction_commit
        self.app = None
        self.dmd = None

        logging.disable(logging.NOTSET)

        super(BaseTestCase, self).beforeTearDown()

    def create(self, context, klass, id):
        """create an instance and attach it to the context passed"""
        inst = klass(id)
        context._setObject(id, inst)
        inst = context._getOb(id)
        return inst
