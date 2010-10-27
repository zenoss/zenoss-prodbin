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
from zope.interface import implements
from zenoss.protocols.twisted.amqp import AMQPFactory
from zenoss.protocols.amqp import publish as blockingpublish
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.guid import generate
from zope.component import getUtility
from zenoss.protocols.protobufs.zep_pb2 import RawEvent as EventProtobuf
from interfaces import IQueuePublisher, IProtobufSerializer
from zenoss.protocols.protobufs.modelevents_pb2 import ModelEventList
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.Zuul.utils import get_dmd


import logging
log = logging.getLogger('zen.queuepublisher')


class ModelChangePublisher(object):
    """
    Keeps track of all the model changes so far in this
    transaction. Do not instantiate this class directly,
    use "getModelChangePublisher" to receive the singleton
    """

    def __init__(self):
        self._eventList = ModelEventList()
        self._eventList.event_uuid = generate()

    def _setFieldProperties(self, ob, event):
        # find out which field we are editing
        proto = event.service
        if isinstance(ob, Device):
            proto = event.device
        elif isinstance(ob, DeviceComponent):
            proto = event.component
        try:
            serializer = IProtobufSerializer(ob)
            return serializer.fill(proto)
        except TypeError:
            import traceback
            tc = traceback.format_exc()
            log.warn("Could not adapt %s to a protobuf serializer: %s " % (ob, tc))
        return proto

    def _createModelEventProtobuf(self, ob, eventType):
        """
        Creates and returns a ModelEvent. This is tightly
        coupled to the modelevent.proto protobuf.
        """
        # eventList will "remember" all the events it creates
        event = self._eventList.events.add()
        event.event_uuid = generate()
        event.type = getattr(event, eventType)
        guid = self._getGUID(ob)

        # Fight with protobuf to set the modelType property
        if isinstance(ob, Device):
            event.model_type = event.DEVICE
            event.device.uuid = guid
        elif isinstance(ob, DeviceComponent):
            event.model_type = event.COMPONENT
            event.component.uuid = guid
        else:
            # it is a service (or organizer)
            event.model_type = event.SERVICE
            event.service.uuid = guid

        return event

    def _getGUID(self, ob):
        return str(IGlobalIdentifier(ob).create())

    def publishAdd(self, ob):
        event = self._createModelEventProtobuf(ob, 'ADDED')
        self._setFieldProperties(ob, event)

    def publishRemove(self, ob):
        self._createModelEventProtobuf(ob, 'REMOVED')

    def publishModified(self, ob):
        event = self._createModelEventProtobuf(ob, 'MODIFIED')
        self._setFieldProperties(ob, event)

    def addToOrganizer(self, ob, org):
        event = self._createModelEventProtobuf(ob, 'ADDRELATION')
        event.add_relation.destination_uuid = self._getGUID(org)

    def removeFromOrganizer(self, ob, org):
        event = self._createModelEventProtobuf(ob, 'REMOVERELATION')
        event.remove_relation.destination_uuid = self._getGUID(org)

    def moveObject(self, ob, fromOb, toOb):
        event = self._createModelEventProtobuf(ob, 'MOVED')
        event.moved.origin = self._getGUID(fromOb)
        event.moved.destination = self._getGUID(toOb)

    @property
    def msg(self):
        return self._eventList


def getModelChangePublisher():
    """
    Adds a synchronizer to the transaction and keep track if a
    synchronizer is on the transaction.
    """
    import transaction
    tx = transaction.get()
    # check to see if there is a publisher on the transaction
    log.debug("getting publisher on tx %s" % tx)
    if not getattr(tx, '_synchronziedPublisher', None):
        tx._synchronziedPublisher = ModelChangePublisher()
        tx.addBeforeCommitHook(PUBLISH_SYNC.beforeCompletionHook, [tx])
    return tx._synchronziedPublisher


# TODO: turn into config options
EXCHANGE = 'zenoss.model'
ROUTE_KEY = 'zenoss.protocols.protobufs.modelevent_pb2.ModelEventList'


class PublishSynchronizer(object):

    def findNonImpactingEvents(self, msg, attribute):
        removeEventIds = []
        addEvents = [event for event in msg.events if event.type == event.ADDED]
        removeEvents = [event for event in msg.events if event.type == event.REMOVED]
        for removeEvent in removeEvents:
            for addEvent in addEvents:
                addComp = getattr(addEvent, attribute)
                removeComp = getattr(removeEvent, attribute)
                if addComp.uuid == removeComp.uuid:
                    removeEventIds.append(addEvent.event_uuid)
                    removeEventIds.append(removeEvent.event_uuid)

        return removeEventIds

    def correlateEvents(self, msg):
        """
        In the case of moving objects we get a ton of add
        and a ton of remove events. This method removes all the
        add/removes where nothing changes.
        NOTE: this only works on devices and components for now.
        Also it expects for devices to have a "move" event associated.
        """
        eventsToRemove = []
        for attribute in ("device", "component"):
            eventsToRemove = eventsToRemove + self.findNonImpactingEvents(msg, attribute)
        if not eventsToRemove:
            return msg

        eventsToRemove = set(eventsToRemove)
        eventsToKeep = [event for event in msg.events if event.event_uuid not in eventsToRemove]

        # protobuf is odd about setting properties, so we have to make a new
        # event list and then copy the events we want into it
        returnMsg = ModelEventList()
        returnMsg.event_uuid = generate()
        for event in eventsToKeep:
            newEvent = returnMsg.events.add()
            newEvent.ParseFromString(event.SerializeToString())
        return returnMsg

    def beforeCompletionHook(self, tx):
        try:
            log.debug("beforeCompletionHook on tx %s" % tx)
            publisher = getattr(tx, '_synchronziedPublisher', None)
            if publisher:
                msg = self.correlateEvents(publisher.msg)
                queuePublisher = getUtility(IQueuePublisher)
                queuePublisher.publish(EXCHANGE, ROUTE_KEY, msg)
            else:
                log.debug("no publisher found on tx %s" % tx)
        finally:
            if hasattr(tx, '_synchronziedPublisher'):
                tx._synchronziedPublisher = None


PUBLISH_SYNC = PublishSynchronizer()


class EventPublisher(object):

    EXCHANGE_NAME = "zenoss.zenevents.raw"

    def publish(self, event):
        serializer = IProtobufSerializer(event)
        proto = EventProtobuf()
        serializer.fill(proto)
        eventClass = "/Unknown"
        if hasattr(event, 'eventClass'):
            eventClass = event.eventClass
        routing_key = "zenoss.zenevent%s" % eventClass.replace('/', '.').lower()
        publisher = getUtility(IQueuePublisher)
        log.debug("About to publish this event to the raw event queue:%s, with this routing key: %s" % (proto, routing_key))
        publisher.publish(self.EXCHANGE_NAME, routing_key, proto, exchange_type='topic')


class AsyncQueuePublisher(object):
    """
    Sends the protobuf to an exchange in a non-blocking manner
    """
    implements(IQueuePublisher)

    def __init__(self):
        self._amqpClient = AMQPFactory()

    def publish(self, exchange, routing_key, message, exchange_type="topic"):
        """
        Publishes a message to an exchange. If twisted is running
        this will use the twisted amqp library, otherwise it will
        be blocking.
        @type  exchange: string
        @param exchange: destination exchange for the amqp server
        @type  routing_key: string
        @param routing_key: Key by which consumers will setup the queus to route
        @type  message: string or Protobuff
        @param message: message we are sending in the queue
        """
        self._amqpClient.send(exchange, routing_key, message, exchange_type)


class BlockingQueuePublisher(object):
    """
    Class that is responsible for sending messages to the amqp exchange.
    """
    implements(IQueuePublisher)

    def publish(self, exchange, routing_key, message, exchange_type="topic"):
        """
        Publishes a message to an exchange. If twisted is running
        this will use the twisted amqp library, otherwise it will
        be blocking.
        @type  exchange: string
        @param exchange: destination exchange for the amqp server
        @type  routing_key: string
        @param routing_key: Key by which consumers will setup the queus to route
        @type  message: string or Protobuff
        @param message: message we are sending in the queue
        """
        blockingpublish(exchange, routing_key, message, exchange_type)


class DummyQueuePublisher(object):
    """
    Class for the unit tests that ignores all messages
    """
    implements(IQueuePublisher)

    def publish(self, exchange, routing_key, message, exchange_type="topic"):
        """
        Publishes a message to an exchange. If twisted is running
        this will use the twisted amqp library, otherwise it will
        be blocking.
        @type  exchange: string
        @param exchange: destination exchange for the amqp server
        @type  routing_key: string
        @param routing_key: Key by which consumers will setup the queus to route
        @type  message: string or Protobuff
        @param message: message we are sending in the queue
        """
        pass

