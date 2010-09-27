from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.guid import generate
from zope.component import getUtility
from Products.ZenUtils.queuemessaging.interfaces import IQueuePublisher, IProtobufSerializer
from zenoss.protocols.protobufs.modelevents_pb2 import ModelEventList,\
    _MODELEVENT_TYPE, _MODELEVENT_MODELTYPE
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent

import logging
log = logging.getLogger('zen.modelchanges')


class ModelChangePublisher(object):
    """
    Keeps track of all the model changes so far in this
    transaction. Do not instantiate this class directly,
    use "getModelChangePublisher" to receive the singleton
    """

    modelTypes =  _MODELEVENT_MODELTYPE.values_by_name
    eventTypes = _MODELEVENT_TYPE.values_by_name

    def __init__(self):
        self._eventList = ModelEventList()
        self._eventList.eventId.uuid = generate()

    def _setFieldProperties(self, ob, event):
        # find out which field we are editing
        proto = event.service
        if isinstance(ob, Device):
            proto = event.device
        elif isinstance(ob, DeviceComponent):
            proto = event.component
        serializer = IProtobufSerializer(ob)
        return serializer.fill(proto)

    def _createModelEventProtobuf(self, ob, eventType):
        """
        Creates and returns a ModelEvent. This is tightly
        coupled to the modelevent.proto protobuf.
        """
        # eventList will "remember" all the events it creates
        event = self._eventList.events.add()
        event.eventId.uuid = generate()
        event.type = self.eventTypes[eventType].number
        guid = self._getGUID(ob)

        # Fight with protobuf to set the modelType property
        modelTypes = self.modelTypes
        if isinstance(ob, Device):
            event.modelType = modelTypes['DEVICE'].number
            event.device.guid.guid = guid
        elif isinstance(ob, DeviceComponent):
            event.modelType = modelTypes['COMPONENT'].number
            event.component.guid.guid = guid
        else:
            # it is a service (or organizer)
            event.modelType = modelTypes['SERVICE'].number
            event.service.guid.guid = guid

        return event

    def _getGUID(self, ob):
        return str(IGlobalIdentifier(ob).getGUID())

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
        event.addRelation.destination.guid = self._getGUID(org)

    def removeFromOrganizer(self, ob, org):
        event = self._createModelEventProtobuf(ob, 'REMOVERELATION')
        event.removeRelation.destination.guid = self._getGUID(org)

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
    log.info("getting publisher on tx %s" % tx)
    if not getattr(tx, '_synchronziedPublisher', None):
        tx._synchronziedPublisher = ModelChangePublisher()
        tx.addBeforeCommitHook(PUBLISH_SYNC.beforeCompletionHook, [tx])
    return tx._synchronziedPublisher


# TODO: turn into config options
EXCHANGE = 'zenoss.model'
ROUTE_KEY = 'zenoss.protocols.protobufs.modelevent_pb2.ModelEventList'


class PublishSynchronizer(object):


    addedID = _MODELEVENT_TYPE.values_by_name['ADDED'].number
    removedID = _MODELEVENT_TYPE.values_by_name['REMOVED'].number

    def findNonImpactingEvents(self, msg, attribute):
        removeEventIds = []
        addEvents = [event for event in msg.events if event.type == self.addedID]
        removeEvents = [event for event in msg.events if event.type == self.removedID]
        for removeEvent in removeEvents:
            for addEvent in addEvents:
                addComp = getattr(addEvent, attribute)
                removeComp = getattr(removeEvent, attribute)
                if addComp.guid.guid == removeComp.guid.guid:
                    removeEventIds.append(addEvent.eventId.uuid)
                    removeEventIds.append(removeEvent.eventId.uuid)

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
        eventsToKeep = [event for event in msg.events if event.eventId.uuid not in eventsToRemove]

        # protobuf is odd about setting properties, so we have to make a new
        # event list and then copy the events we want into it
        returnMsg = ModelEventList()
        returnMsg.eventId.uuid = generate()
        for event in eventsToKeep:
            newEvent = returnMsg.events.add()
            newEvent.ParseFromString(event.SerializeToString())
        return returnMsg

    def beforeCompletionHook(self, tx):
        try:
            log.info("beforeCompletionHook on tx %s" % tx)
            publisher = getattr(tx, '_synchronziedPublisher', None)
            if publisher:
                msg = self.correlateEvents(publisher.msg)
                queuePublisher = getUtility(IQueuePublisher)
                queuePublisher.publish(EXCHANGE, ROUTE_KEY, msg)
            else:
                log.info("no publisher found on tx %s" % tx)
        finally:
            if hasattr(tx, '_synchronziedPublisher'):
                tx._synchronziedPublisher = None


PUBLISH_SYNC = PublishSynchronizer()
