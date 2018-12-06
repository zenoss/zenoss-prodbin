##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import unittest
from mock import patch, Mock
import sys

from twisted.python.failure import Failure
from twisted.cred import credentials
from twisted.spread import pb

from Products.ZenTestCase.BaseTestCase import ZenossTestCaseLayer, BaseTestCase
from Products.ZenUtils.Driver import drive
from Products.ZenHub.PBDaemon import RemoteException, RemoteConflictError
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from Products.ZenMessaging.queuemessaging.publisher import (
    DummyQueuePublisher, EventPublisher
)

from Products.ZenHub.zenhub import (
    ZenHub,
    IEventPublisher,
)
# Import from zenhub before importing twisted.internet.reactor
from twisted.internet import reactor

PATH = {'src': 'Products.ZenHub.zenhub'}
count = 0


def stop(ignored=None, connector=None):
    if isinstance(ignored, Exception):
        raise ignored
    if reactor.running:
        if getattr(reactor, 'threadpool', None) is not None:
            reactor.threadpool.stop()
            reactor.threadpool = None
        reactor.crash()
    if connector:
        connector.disconnect()


class TestClient(pb.Referenceable):

    success = False
    svc = 'Products.ZenHub.tests.TestService'

    def __init__(self, tester, port):
        self.tester = tester
        factory = pb.PBClientFactory()
        self.connector = reactor.connectTCP("localhost", port, factory)
        creds = credentials.UsernamePassword("admin", "zenoss")
        d = factory.login(creds, client=self)
        d.addCallback(self.connected)
        d.addErrback(self.bad)

    def connected(self, perspective):
        d = perspective.callRemote('getService', self.svc, 'localhost', self)
        d.addCallback(self.test)
        d.addErrback(self.bad)

    def bad(self, reason):
        stop(connector=self.connector)
        self.tester.fail('error: ' + str(reason.value))

    def test(self, service):
        def Test(driver):
            data = ('Some Data', 17)
            yield service.callRemote('echo', data)
            self.tester.assertEqual(driver.next(), data)
            self.success = True
        drive(Test).addBoth(stop, connector=self.connector)


class SendEventClient(TestClient):
    svc = 'EventService'

    def test(self, service):
        def Test(driver):

            evt = dict(device='localhost',
                       severity='5',
                       summary='This is a test message')
            yield service.callRemote('sendEvents', [evt])
            self.tester.assertEqual(driver.next(), 1)
            self.success = True
        drive(Test).addBoth(stop, connector=self.connector)


class TestZenHub(BaseTestCase):

    layer = ZenossTestCaseLayer

    base = 7000
    xbase = 8000

    def afterSetUp(t):
        super(TestZenHub, t).afterSetUp()
        global count
        count += 1
        base = t.base + count
        xbase = t.xbase + count

        args = ['run', '--pbport=%d' % base, '--xmlrpcport=%d' % xbase, '--workers=0']
        argv_patcher = patch.object(sys, 'argv', args)
        t.argv = argv_patcher.start()
        t.addCleanup(argv_patcher.stop)

        getutility_patcher = patch(
            '{src}.getUtility'.format(**PATH),
            autospec=True, side_effect=get_utility_mock
        )
        t.getUtility = getutility_patcher.start()
        t.addCleanup(getutility_patcher.stop)

        invalidation_manager_patcher = patch(
            '{src}.InvalidationManager'.format(**PATH), autospec=True
        )
        invalidation_manager_patcher.start()
        t.addCleanup(invalidation_manager_patcher.stop)

        t.zenhub = ZenHub()

    def beforeTearDown(t):
        super(TestZenHub, t).beforeTearDown()

    def testPbRegistration(t):
        from twisted.spread.jelly import unjellyableRegistry
        t.assertTrue('DataMaps.ObjectMap' in unjellyableRegistry)
        t.assertTrue(
            'Products.DataCollector.plugins.DataMaps.ObjectMap'
            in unjellyableRegistry
        )

    def testSendEvent(t):
        EventPublisher._publisher = DummyQueuePublisher()
        client = SendEventClient(t, t.base + count)
        t.assertFalse(client.success)
        t.zenhub.main()
        t.assertTrue(client.success)


def get_utility_mock(utility):
    if utility is IQueuePublisher:
        return DummyQueuePublisher()
    if utility is IEventPublisher:
        return Mock(name='IEventPublisher')
    if utility == 'IInvalidationProcessor':
        return Mock(name='IInvalidationProcessor')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZenHub))
    return suite
