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

from Products.ZenEvents.events2.fields import EventField
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.DataRoot import DataRoot
from Products.ZenEvents.events2.proxy import ZepRawEventProxy
from Products.ZenUtils.guid.interfaces import IGUIDManager, IGlobalIdentifier
from Products.Zuul.interfaces import ICatalogTool
from Products.AdvancedQuery import Eq, MatchGlob, Or
from zope.component import getUtilitiesFor
from Acquisition import aq_chain
from Products.ZenEvents import ZenEventClasses

from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_CLOSED,
    STATUS_DROPPED,
)

import logging
log = logging.getLogger("zen.eventd")

class ProcessingException(Exception):
    def __init__(self, message, event):
        super(ProcessingException, self).__init__(message)
        self.event = event

class DropEvent(ProcessingException):
    """
    Raised when an event should be dropped from the queue.
    """
    pass

class EventLoggerAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds the event UUID to the log output.
    """
    def process(self, msg, kwargs):
        msg = '[{event_uuid}] {msg}'.format(event_uuid=self.extra['event_uuid'], msg=msg)
        return msg, kwargs

class Manager(object):
    """
    Provides lookup access to processing pipes and performs caching.
    """

    ELEMENT_TYPE_MAP = {
        DEVICE : Device,
        COMPONENT : DeviceComponent,
    }

    def __init__(self, dmd):
        self.dmd = dmd
        self._guidManager = IGUIDManager(self.dmd)

        self._devices = self.dmd._getOb('Devices')
        self._networks = self.dmd._getOb('Networks')
        self._events = self.dmd._getOb('Events')

        self._catalogs = {
            DEVICE : self._devices,
        }

    def getEventClassOrganizer(self, eventClassName):
        try:
            return self._events.getOrganizer(eventClassName)
        except KeyError:
            # Unknown organizer
            return None

    def lookupEventClass(self, eventContext):
        """
        Find a Device's EventClass
        """
        if eventContext.deviceObject:
            return self._events.lookup(eventContext.eventProxy, eventContext.deviceObject)

    def getElementByUuid(self, uuid):
        """
        Get a Device/Component by UUID
        """
        if uuid:
            return self._guidManager.getObject(uuid)

    def getElementUuidById(self, catalog, element_type_id, id):
        """
        Find element by ID but only cache UUID. This forces us to lookup elements
        each time by UUID (pretty fast) which gives us a chance to see if the element
        has been deleted.
        """
        cls = self.ELEMENT_TYPE_MAP.get(element_type_id)
        if cls:
            catalog = catalog or self._catalogs.get(element_type_id)
            if catalog:
                results = ICatalogTool(catalog).search(cls, query=Or(Eq('id', id),Eq('name',id)))

                if results.total:
                    return results.results.next().uuid

    def getElementById(self, catalog, element_type_id, id):
        """
        Find element by ID, first checking a cache for UUIDs then using that UUID
        to load the element. If the element can't be found by UUID, the UUID
        cache is cleared and lookup tried again.
        """
        uuid = self.getElementUuidById(catalog, element_type_id, id)
        if uuid:
            element = self.getElementByUuid(uuid)
            if not element:
                # Lookup cache must be invalid, try looking up again
                self.getElementUuidById.clear()
                log.warning('Clearing ElementUuidById cache becase we could not find %s' % uuid)
                uuid = self.getElementUuidById(catalog, element_type_id, id)
                element = self.getElementByUuid(uuid)
            return element

    def getElementUuid(self, obj):
        if obj:
            return IGlobalIdentifier(obj).getGUID()

    def findDeviceUuid(self, identifier, ipAddress):
        """
        This will return the device's
        @type  identifier: string
        @param identifier: The IP address or id of a device
        @type  ipaddress: string
        @param ipaddress: The known ipaddress of the device
        """
        cat = ICatalogTool(self._devices)

        querySet = Or(MatchGlob('id', identifier),
                    MatchGlob('name', identifier),
                    Eq('ipAddress', identifier),
                    Eq('ipAddress', ipAddress))

        results = cat.search(types=Device, query=querySet, limit=1)

        if results.total:
            return results.results.next().uuid
        else:
            querySet = Or(Eq('ipAddress', identifier),
                        Eq('ipAddress', ipAddress))

            # search the components
            results = cat.search(types=DeviceComponent, query=querySet, limit=1)
            if results.total:
                return self.getElementUuid(results.results.next().getObject().device())
            else:
                return None

    def findDevice(self, identifier, ipAddress):
        uuid = self.findDeviceUuid(identifier, ipAddress)
        if uuid:
            return self.getElementByUuid(uuid)

    def getUuidsOfPath(self, node):
        """
        Looks up all the UUIDs in the tree path of an Organizer
        """
        uuids = set([])
        acquisition_chain = []
        for n in aq_chain(node.primaryAq()):
            if isinstance(n, DataRoot):
                acquisition_chain.pop()
                break
            acquisition_chain.append(n)

        if acquisition_chain:
            for obj in filter(None, acquisition_chain):
                try:
                    uuids.add(self.getElementUuid(obj))
                except TypeError:
                    log.debug("Unable to get a uuid for %s " % obj)

        return uuids

class EventContext(object):
    """
    Maintains the event context while processing.
    """
    def __init__(self, log, zepRawEvent):
        self._zepRawEvent = zepRawEvent
        self._event = self._zepRawEvent.raw_event
        self._eventProxy = ZepRawEventProxy(self._zepRawEvent)

        # If this event is for a device, it will be attached here
        self._deviceObject = None
        self._componentObject = None
        self.log = EventLoggerAdapter(log, { 'event_uuid' : self._event.uuid })

    def setDeviceObject(self, device):
        self._deviceObject = device

    def refreshClearClasses(self):
        self._eventProxy._refreshClearClasses()
        
    @property
    def deviceObject(self):
        return self._deviceObject

    def setComponentObject(self, component):
        self._componentObject = component

    @property
    def componentObject(self):
        return self._componentObject

    @property
    def zepRawEvent(self):
        return self._zepRawEvent

    @property
    def event(self):
        return self._event

    @property
    def eventProxy(self):
        """
        A EventProxy that wraps the event protobuf and makes it look like an old style event.
        """
        return self._eventProxy

class EventProcessorPipe(object):
    """
    An event context handler that is called in a chain.
    """
    dependencies = []

    def __init__(self, manager):
        self._manager = manager

    def __call__(self, eventContext):
        """
        Called in a chain, must return modified eventContext.
        """
        raise NotImplementedError()

class CheckInputPipe(EventProcessorPipe):
    """
    Validates that the event has required fields.
    """
    REQUIRED_EVENT_FIELDS = (EventField.ACTOR, EventField.SUMMARY, EventField.SEVERITY)

    def __call__(self, eventContext):
        missingFields = []
        for field in self.REQUIRED_EVENT_FIELDS:
            if not eventContext.event.HasField(field):
                missingFields.append(field)

        if missingFields:
            raise DropEvent('Required event fields %s not found' % ','.join(missingFields), eventContext.event)

        # Make sure summary and message are populated
        if not eventContext.event.HasField('message') and eventContext.event.HasField('summary'):
            eventContext.event.message = eventContext.event.summary
        elif not eventContext.event.HasField('summary') and eventContext.event.HasField('message'):
            eventContext.event.summary = eventContext.event.message[:255]

        return eventContext


class IdentifierPipe(EventProcessorPipe):
    """
    Resolves element uuids and identifiers to make sure both are populated.
    """

    dependencies = [CheckInputPipe]

    def _resolveElement(self, catalog, eventContext, type_id_field, identifier_field, uuid_field):
        """
        Lookup an element by identifier or uuid and make sure both
        identifier and uuid are set.
        """
        actor = eventContext.event.actor
        if ( actor.HasField(type_id_field) and
            not (actor.HasField(identifier_field) and actor.HasField(uuid_field)) ):
            if actor.HasField(uuid_field):
                uuid = getattr(actor, uuid_field, None)
                element = self._manager.getElementByUuid(uuid)
                if element:
                    eventContext.log.debug('Identified element %s by uuid %s', element, uuid)
                    setattr(actor, identifier_field, element.id)
                else:
                    eventContext.log.warning('Could not find element by uuid %s', uuid)

            elif actor.HasField(identifier_field):
                type_id = getattr(actor, type_id_field, None)
                identifier = getattr(actor, identifier_field, None)
                if type_id == DEVICE:
                    element_uuid = self._manager.findDeviceUuid(identifier, eventContext.eventProxy.ipAddress)
                else:
                    element_uuid = self._manager.getElementUuidById(catalog, type_id, identifier)

                if element_uuid:
                    eventContext.log.debug('Identified element %s by id %s', element_uuid, identifier)
                    setattr(actor, uuid_field, element_uuid)
                else:
                    eventContext.log.debug('Could not find element type %s with id %s', type_id, identifier)

    def __call__(self, eventContext):
        eventContext.log.debug('Identifying event')

        actor = eventContext.event.actor

        # Get element, most likely a Device
        self._resolveElement(
                None,
                eventContext,
                EventField.Actor.ELEMENT_TYPE_ID,
                EventField.Actor.ELEMENT_IDENTIFIER,
                EventField.Actor.ELEMENT_UUID
            )


        # Get element, most likely a Component
        self._resolveElement(
                self._manager.getElementByUuid(actor.element_uuid) if actor.HasField(EventField.Actor.ELEMENT_UUID) else None,
                eventContext,
                EventField.Actor.ELEMENT_SUB_TYPE_ID,
                EventField.Actor.ELEMENT_SUB_IDENTIFIER,
                EventField.Actor.ELEMENT_SUB_UUID
            )

        return eventContext

class AddDeviceContextPipe(EventProcessorPipe):
    """
    Adds device and component info to the context and event proxy.
    """
    dependencies = [IdentifierPipe]

    FIELDS = (
        (EventField.Actor.ELEMENT_TYPE_ID, EventField.Actor.ELEMENT_UUID),
        (EventField.Actor.ELEMENT_SUB_TYPE_ID, EventField.Actor.ELEMENT_SUB_UUID),
    )

    def _addDeviceContext(self, eventContext, device):
        eventContext.eventProxy.ipAddress = eventContext.eventProxy.ipAddress or device.manageIp
        eventContext.eventProxy.prodState = device.productionState
        eventContext.eventProxy.DevicePriority = device.getPriority()

        eventContext.eventProxy.setReadOnly('Location', device.getLocationName())
        eventContext.eventProxy.setReadOnly('DeviceClass', device.getDeviceClassName())
        eventContext.eventProxy.setReadOnly('DeviceGroups', '|'+'|'.join(device.getDeviceGroupNames()))
        eventContext.eventProxy.setReadOnly('Systems', '|'+'|'.join(device.getSystemNames()))

        eventContext.setDeviceObject(device)

    def _addComponentContext(self, eventContext, component):
        eventContext.setComponentObject(component)

    def _findElement(self, eventContext, type_id):
        actor = eventContext.event.actor
        for type_id_field, uuid_field in self.FIELDS:
            if ( actor.HasField(type_id_field)
                 and actor.element_type_id == type_id
                 and actor.HasField(uuid_field) ):

                 return self._manager.getElementByUuid(actor.element_uuid)

    def __call__(self, eventContext):
        eventContext.log.debug('Adding device context')

        device = self._findElement(eventContext, DEVICE)
        if device:
            self._addDeviceContext(eventContext, device)

        component = self._findElement(eventContext, COMPONENT)
        if component:
            self._addComponentContext(eventContext, component)

        return eventContext

class SerializeContextPipe(EventProcessorPipe):
    """
    Takes fields added to the eventProxy that couldn't directly be mapped out of the
    proxy and applies them to the event protobuf.
    """
    dependencies = [AddDeviceContextPipe]

    def __call__(self, eventContext):
        eventContext.log.debug('Saving context back to event')
        return eventContext

class FingerprintPipe(EventProcessorPipe):
    """
    Calculates event's fingerprint/dedupid.
    """

    DEFAULT_FINGERPRINT_FIELDS = ('device', 'component', 'eventClass', 'eventKey', 'severity')
    NO_EVENT_KEY_FINGERPRINT_FIELDS = ('device', 'component', 'eventClass', 'severity', 'summary')

    dependencies = [AddDeviceContextPipe]

    def __call__(self, eventContext):
        event = eventContext.event

        if not event.HasField(EventField.FINGERPRINT):
            dedupFields = self.DEFAULT_FINGERPRINT_FIELDS
            if not (event.HasField(EventField.EVENT_KEY) and
                    getattr(event, EventField.EVENT_KEY, None)):
                dedupFields = self.NO_EVENT_KEY_FINGERPRINT_FIELDS

            dedupIdList = [str(getattr(eventContext.eventProxy, field, '')) for field in dedupFields]

            eventContext.eventProxy.dedupid = '|'.join(dedupIdList)

            eventContext.log.debug('Created dedupid of %s from %s', eventContext.eventProxy.dedupid, dedupIdList)

        return eventContext

class TransformPipe(EventProcessorPipe):
    dependencies = [AddDeviceContextPipe]

    EVENT_CLASS_TAG = 'zenoss.event.event_class'

    ACTION_HISTORY = 'history'
    ACTION_DROP = 'drop'
    ACTION_STATUS = 'status'
    ACTION_HEARTBEAT = 'heartbeat'
    ACTION_LOG = 'log'
    ACTION_ALERT_STATE = 'alert_state'
    ACTION_DETAIL = 'detail'

    ACTION_STATUS_MAP = {
        ACTION_HISTORY : STATUS_CLOSED,
        ACTION_STATUS : STATUS_NEW,
        ACTION_DROP : STATUS_DROPPED,
    }

    def _tagEventClasses(self, eventContext, eventClass):
        """
        Adds a set of tags for the hierarchy of event classes for this event
        NOTE: We must tag the event classes at this part of the pipeline
        before a mapping has been applied otherwise the mapping instance
        won't be tagged, just the Event Class that was mapped.
        """
        try:
            eventClassUuids = self._manager.getUuidsOfPath(eventClass)
            if eventClassUuids:
                eventContext.eventProxy.tags.addAll(self.EVENT_CLASS_TAG, eventClassUuids)
        except (KeyError, AttributeError):
            log.info("Event has nonexistent event class %s." % eventClass)

    def __call__(self, eventContext):
        if eventContext.deviceObject:
            eventContext.log.debug('Mapping and Transforming event')
            evtclass = self._manager.lookupEventClass(eventContext)
            if evtclass:
                self._tagEventClasses(eventContext, evtclass)
                evtclass.applyExtraction(eventContext.eventProxy)
                evtclass.applyValues(eventContext.eventProxy)
                evtclass.applyTransform(eventContext.eventProxy, eventContext.deviceObject)

        return eventContext

class EventPluginPipe(EventProcessorPipe):
    def __init__(self, manager, pluginInterface):
        super(EventPluginPipe, self).__init__(manager)

        self._eventPlugins = tuple(getUtilitiesFor(pluginInterface))

    def __call__(self, eventContext):
        for name, plugin in self._eventPlugins:
            try:
                plugin.apply(eventContext._eventProxy, self._manager.dmd)
            except Exception as e:
                eventContext.log.error('Event plugin %s encountered an error -- skipping.' % name)
                eventContext.log.exception(e)
                continue

        return eventContext

class EventTagPipe(EventProcessorPipe):

    DEVICE_TAGGERS = {
        'zenoss.device.device_class' : lambda device: device.deviceClass(),
        'zenoss.device.location' : lambda device: device.location(),
        'zenoss.device.system' : lambda device: device.systems(),
        'zenoss.device.group' : lambda device: device.groups(),
    }

    def __call__(self, eventContext):
        device = eventContext.deviceObject
        if device:
            for tagType, func in self.DEVICE_TAGGERS.iteritems():
                objList = func(device)
                if objList:
                    if not isinstance(objList, list):
                        objList = [objList]
                    for obj in objList:
                        uuids = self._manager.getUuidsOfPath(obj)
                        if uuids:
                            eventContext.eventProxy.tags.addAll(tagType, uuids)

        eventClassName = eventContext.eventProxy.eventClass
        # Set event class to Unknown if not specified
        if not eventClassName:
            eventContext.eventProxy.eventClass = eventClassName = ZenEventClasses.Unknown

        # If we failed to tag an event class - can happen if there is not a device
        # or event class is not defined.
        if not eventContext.eventProxy.tags.getByType(TransformPipe.EVENT_CLASS_TAG):
            eventClass = self._manager.getEventClassOrganizer(eventClassName)
            if eventClass:
                eventClassUuids = self._manager.getUuidsOfPath(eventClass)
                eventContext.eventProxy.tags.addAll(TransformPipe.EVENT_CLASS_TAG, eventClassUuids)

        return eventContext

class ClearClassRefreshPipe(EventProcessorPipe):

    def __call__(self, eventContext):
        eventContext.refreshClearClasses()
        return eventContext
