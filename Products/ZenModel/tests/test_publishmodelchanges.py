######################################################################
#
# Copyright 2010 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import logging
import transaction
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.interface import implements
from Products.ZenUtils.queuemessaging.interfaces import IQueuePublisher
from Products.ZenModel.ChangeEvents.publisher import getModelChangePublisher, PUBLISH_SYNC
from zenoss.protocols.protobufs.modelevents_pb2 import ModelEventList
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.WinService import WinService

log = logging.getLogger("zen.dynamicservices")


class MockQueuePublisher(object):
    """
    This is the fake queue we are putting in place for the unit tests to test
    transactions.
    """
    implements(IQueuePublisher)

    def __init__(self):
        self.msgs = []

    def publish(self, exchange, routing_key, msg):
        self.msgs.append( (exchange, routing_key, msg))


class TestPublishModelChanges(BaseTestCase):

    def setUp(self):
        super(TestPublishModelChanges, self).setUp()
        self.publisher = getModelChangePublisher()
        from zope.component import getGlobalSiteManager
        # register the component
        gsm = getGlobalSiteManager()
        queue = MockQueuePublisher()
        gsm.registerUtility(queue, IQueuePublisher)
        self.queue = queue
        # create a dummy device
        self.device = self.dmd.Devices.createInstance('testDevice')
        self.publisher.publishAdd(self.device)


    def tearDown(self):
        super(TestPublishModelChanges, self).tearDown()
        self.publisher = None
        self.device = None
        self.queue = None

    def testObjectNotifyEvent(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.publishModified(self.device)
        self.assertEqual(len(self.publisher.msg.events), 1)

    def testObjectRemovedEvent(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.publishRemove(self.device)
        self.assertEqual(len(self.publisher.msg.events), 1)

    def testAddToOrganizer(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.addToOrganizer(self.device, self.dmd.Devices)
        self.publisher.removeFromOrganizer(self.device, self.dmd.Devices)
        self.assertEqual(len(self.publisher.msg.events), 2)

    def testCompletingTransaction(self):
        # get some stuff in the queue
        self.testAddToOrganizer()
        sync = PUBLISH_SYNC
        sync.beforeCompletionHook(transaction.get())
        publisher = getModelChangePublisher()
        self.assertEqual(len(publisher.msg.events), 0)
        self.assertEqual(len(self.queue.msgs), 1, " should have one transaction published to the queue")

    def testDeviceClassMove(self):
        """
        This test is a little tricky. When we move device classes
        an ADD, REMOVE, and MOVE events are all fired.
        We need to coordinate those to make sure that only
        one MOVE event is sent
        """
        deviceClass = self.device.deviceClass()
        target = DeviceClass('pepe')
        deviceClass._setObject(target.id, target)
        # clear the event list
        self.publisher._eventList = ModelEventList()

        # we are going to simulate a device moving from device class
        # by first adding/removing a component then the deviec
        # then sending the device move event
        # only one move event should show up
        component = WinService('foo')
        device = self.device
        # component
        self.publisher.publishRemove(component)
        self.publisher.publishAdd(component)

        # device
        self.publisher.publishRemove(device)
        self.publisher.publishAdd(device)

        # make sure only 1 event is fired
        self.publisher.moveObject(device, deviceClass, target)
        sync = PUBLISH_SYNC
        msg = sync.correlateEvents(self.publisher.msg)
        self.assertEqual(len(msg.events), 1, "should only be one move event")

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPublishModelChanges))
    return suite
