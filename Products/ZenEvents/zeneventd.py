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
__doc__='''zeneventd

Apply up-front preprocessing to events.

'''

import Globals
import os

from zope.component import getUtilitiesFor
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from zenoss.protocols.protobufs.zep_pb2 import RawEvent, ZepRawEvent
from zenoss.protocols.protobufs.zep_pb2 import EventActor, SEVERITY_CLEAR
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_SUPPRESSED,
    STATUS_CLOSED,
    STATUS_CLEARED,
    STATUS_DROPPED,
    STATUS_AGED)
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT, SERVICE
from zenoss.protocols.amqpconfig import getAMQPConfiguration
from twisted.internet import reactor, defer
from twisted.internet.error import ReactorNotRunning
from zope.interface import implements

from Products.ZenEvents.MySqlSendEvent import EventTransformer
TRANSFORM_EVENT_IN_EVENTD = True

from Products.ZenEvents.transformApi import Event as TransformEvent
from Products.ZenUtils.guid.interfaces import IGUIDManager, IGlobalIdentifier
from Products.Zuul.interfaces import ICatalogTool, IInfo
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.AdvancedQuery import Eq

from Products.ZenEvents.interfaces import IEventPlugin

import logging
log = logging.getLogger("zen.eventd")

CLEAR_CLASSES = "_CLEAR_CLASSES"

statusConvertToEnum = {
    "new" : STATUS_NEW,
    "ack" : STATUS_ACKNOWLEDGED,
    "suppressed" : STATUS_SUPPRESSED,
    "closed" : STATUS_CLOSED,
    "cleared" : STATUS_CLEARED,
    "dropped" : STATUS_DROPPED,
    "aged" : STATUS_AGED,
}
statusConvertToString = dict((v,k) for k,v in statusConvertToEnum.items())

# add for legacy compatibility
statusConvertToEnum['status'] = STATUS_NEW
statusConvertToEnum['history'] = STATUS_CLOSED
statusConvertToEnum['drop'] = STATUS_DROPPED

class ProcessEventMessageTask(object):
    implements(IQueueConsumerTask)

    """
    queueConsumer = Attribute("The consumer this task is proceessing a message for")
    exchange = Attribute("The name of the exchange the task wants to listen to")
    routing_key = Attribute("The Routing Key used to bind the queue to the exchange")
    queue_name = Attribute("The name of the queue that this task will listen to.")
    exchange_type = Attribute("The type of exchange (topic, direct, fanout)")
    """

    def __init__(self):
        config = getAMQPConfiguration()
        # set by the constructor of queueConsumer
        self.queueConsumer = None

        queue = config.getQueue("$RawZenEvents")
        binding = queue.getBinding("$RawZenEvents")
        self.exchange = binding.exchange.name
        self.routing_key = binding.routing_key
        self.exchange_type = binding.exchange.type
        self.queue_name = queue.name

        self.dest_exchange = config.getExchange("$ZepZenEvents")
        self.dest_routing_key_prefix = 'zenoss.zenevent'

    def eventDetailsToDict(self, event):
        # convert event details name-values to temporary dict
        event_detailmap = {}
        for ed in event.details:
            if ed.value:
                if len(ed.value) == 1:
                    event_detailmap[ed.name] = ed.value[0]
                else:
                    event_detailmap[ed.name] = list(ed.value)
            else:
                event_detailmap[ed.name] = None
        return event_detailmap

    def eventDetailDictToNameValues(self, event, event_detailmap):
        # convert event details temporary dict back to protobuf name-value
        del event.details[:]

        isiterable = lambda v : hasattr(v, '__iter__')
        for k,v in event_detailmap.items():
            ed = event.details.add()
            ed.name = k
            if v is not None:
                if isiterable(v):
                    ed.value.extend(list(v))
                else:
                    ed.value.append(v)

    def addEventControlDetails(self, event, details):
        if not CLEAR_CLASSES in details or details[CLEAR_CLASSES] is None:
            details[CLEAR_CLASSES] = []

        if isinstance(details[CLEAR_CLASSES], basestring):
            details[CLEAR_CLASSES] = details[CLEAR_CLASSES].split(',')

        if (event.severity == SEVERITY_CLEAR and
            hasattr(event, 'event_class') and  
            event.event_class and
            event.event_class not in details[CLEAR_CLASSES]):
            details[CLEAR_CLASSES].append(event.event_class)

    def removeEventControlDetails(self, event, details):
        for name in [CLEAR_CLASSES,] + "_DEDUP_FIELDS _REQUIRED_FIELDS".split():
            if name in details:
                del details[name]

    def getObjectUuid(self, obj):
        if obj is not None:
            return IGlobalIdentifier(obj).getGUID()
        else:
            return ''

    def getObjectForUuid(self, uuid):
        gm = IGUIDManager(self.dmd)
        return gm.getObject(uuid)

    def getObjectUuidForId(self, objid, idattr, objcls, parentUuid=None):
        element = None

        # if a parent uuid was provided, get its corresponding object to scope search;
        # else just use the global dmd
        if parentUuid:
            catalog = self.getObjectForUuid(parentUuid)
        else:
            catalog = self.dmd

        # search for object by identifying attribute
        result = ICatalogTool(catalog).search(objcls, query=Eq(idattr, objid)).results

        try:
            element = result.next().getObject()
        except StopIteration:
            pass
        if element:
            return self.getObjectUuid(element)

        return ''

    def resolveEntityIdAndUuid(self, entityType, identifier, uuid, parentUuid=None):
        if uuid:
            # lookup device by uuid, fill in identifier
            element  = self.getObjectForUuid(uuid)
            if element:
                identifier = IInfo(element).name
        else:
            # lookup device by identifier, fill in uuid
            cls = { DEVICE    : Device, 
                    COMPONENT : DeviceComponent, 
                    SERVICE   : None }[entityType]
            uuid = self.getObjectUuidForId(identifier, 'id', cls, parentUuid)

        return identifier, uuid

    def getIdentifiersForUuids(self, evtproto):
        # translate uuids to identifiers, if not provided
        if evtproto.actor.element_type_id:
            ident,uuid = self.resolveEntityIdAndUuid(evtproto.actor.element_type_id,
                                evtproto.actor.element_identifier,
                                evtproto.actor.element_uuid)
            evtproto.actor.element_identifier = ident
            evtproto.actor.element_uuid = uuid
        if evtproto.actor.element_sub_type_id:
            ident,uuid = self.resolveEntityIdAndUuid(evtproto.actor.element_sub_type_id, 
                                evtproto.actor.element_sub_identifier,
                                evtproto.actor.element_sub_uuid,
                                evtproto.actor.element_uuid)
            evtproto.actor.element_sub_identifier = ident
            evtproto.actor.element_sub_uuid = uuid

    def extractActorElements(self, evtproto, event):
        elementTypeAttrMap = { DEVICE : 'device', COMPONENT : 'component', SERVICE : 'service' }
        # initialize element attributes to ''
        for attr in elementTypeAttrMap.values():
            setattr(event, attr, '')

        # set primary element attribute
        if evtproto.actor.element_type_id and evtproto.actor.element_identifier:
            attr = elementTypeAttrMap[evtproto.actor.element_type_id]
            log.debug("Setting event attribute %s to '%s'", attr, evtproto.actor.element_identifier)
            setattr(event, attr, evtproto.actor.element_identifier)

        # set secondary element attribute
        if evtproto.actor.element_sub_type_id and evtproto.actor.element_sub_identifier:
            attr = elementTypeAttrMap[evtproto.actor.element_sub_type_id]
            log.debug("Setting event attribute %s to '%s'", attr, evtproto.actor.element_sub_identifier)
            setattr(event, attr, evtproto.actor.element_sub_identifier)

    def updateActorReferences(self, evtproto, evt_changes):
        elementTypeAttrMap = { DEVICE : 'device', COMPONENT : 'component', SERVICE : 'service' }
        if evtproto.actor.element_type_id:
            attr = elementTypeAttrMap[evtproto.actor.element_type_id]
            if attr in evt_changes:
                evtproto.actor.element_identifier = evt_changes[attr]
                evtproto.actor.element_uuid = ''
        if evtproto.actor.element_sub_type_id:
            attr = elementTypeAttrMap[evtproto.actor.element_sub_type_id]
            if attr in evt_changes:
                evtproto.actor.element_sub_identifier = evt_changes[attr]
                evtproto.actor.element_sub_uuid = ''
        self.getIdentifiersForUuids(evtproto)

    def addEventIndexTerms(self, actor, uuidTags, evtDetails):

        def addTag(tagtype, taguuid, tags_add=uuidTags.add):
            if taguuid:
                newtag = tags_add()
                newtag.type = tagtype
                newtag.uuid = taguuid

        def addDetail(detname, detvalue, det_add=evtDetails.add):
            ed = det_add()
            ed.name = detname
            ed.value.append(detvalue)

        # extract device, component, and/or service from actor uuid's
        elementrefs = { DEVICE : None, COMPONENT : None, SERVICE : None }
        for elementType in (DEVICE, COMPONENT, SERVICE):
            if actor.element_type_id == elementType and actor.element_uuid:
                obj = self.getObjectForUuid(actor.element_uuid)
                elementrefs[elementType] = obj
                actor.element_identifier = obj.id
            if actor.element_sub_type_id == elementType and actor.element_sub_uuid:
                subobj = self.getObjectForUuid(actor.element_sub_uuid)
                elementrefs[elementType] = subobj
                actor.element_sub_identifier = subobj.id

        # set device search terms
        dmd = self.dmd
        device = elementrefs[DEVICE]
        if device is not None:
            deviceuuid = self.getObjectUuid(device)
            addTag('zenoss.device', deviceuuid)

            devclassRoot = dmd.Devices
            devclass = device.deviceClass()
            while devclass != devclassRoot:
                addTag('zenoss.device.device_class', self.getObjectUuid(devclass))
                devclass = devclass.getPrimaryParent()

            locationRoot = dmd.Locations
            locn = device.location()
            while locn and locn != locationRoot:
                addTag('zenoss.device.location', self.getObjectUuid(locn))
                locn = locn.getPrimaryParent()

            # get uuids for device groups, systems, and (later) services
            systemRoot = dmd.Systems
            for s in device.systems():
                while s != systemRoot:
                    addTag('zenoss.device.system', self.getObjectUuid(s))
                    s = s.getPrimaryParent()

            groupRoot = dmd.Groups
            for g in device.groups():
                while g != groupRoot:
                    addTag('zenoss.device.group', self.getObjectUuid(g))
                    g = g.getPrimaryParent()

            # add event details for other searchable device attributes
            addDetail('zenoss.device.production_state', str(device.productionState))
            addDetail('zenoss.device.priority', str(device.priority))

        # set component search terms
        component = elementrefs[COMPONENT]
        if component is not None:
            addTag('zenoss.component', self.getObjectUuid(component))

        # set service search terms
        service = elementrefs[SERVICE]
        if service  is not None:
            addTag('zenoss.service', self.getObjectUuid(service))


    def publishEvent(self, event):
        return self.queueConsumer.publishMessage("$ZepZenEvents",
                                                 self.dest_routing_key_prefix +
                                                 event.raw_event.event_class.replace('/','.').lower(),
                                                 event)

    @defer.inlineCallbacks
    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        self.dmd._p_jar.sync()
        try:
            # read message from queue; if MARKER, just return
            if message.content.body == self.queueConsumer.MARKER:
                return

            # extract event from message body
            zepevent = ZepRawEvent()
            zepevent.raw_event.ParseFromString(message.content.body)
            event = zepevent.raw_event
            evtdetails = self.eventDetailsToDict(event)
            log.debug("Received event: %s", dict((f.name,getattr(event,f.name,None)) for f in RawEvent.DESCRIPTOR.fields))
            log.debug("- with actor: %s", dict((f.name, getattr(event.actor,f.name,None)) for f in EventActor.DESCRIPTOR.fields))
            log.debug("- with details: %s", evtdetails)

            # ensure required fields are present, otherwise discard this event
            for reqdattr in "actor summary severity".split():
                if not str(getattr(event, reqdattr)):
                    log.error("Required event field %s not found -- ignoring event", reqdattr)
                    self.logEvent(log.error, event, evtdetails)
                    return

            # add details for control during event processing
            self.addEventControlDetails(event, evtdetails)

            if TRANSFORM_EVENT_IN_EVENTD:
                # initialize adapter with event properties
                event_attributes = dict((f.name,getattr(event,f.name,None)) for f in RawEvent.DESCRIPTOR.fields)
                event_attributes["status"] = statusConvertToString[event_attributes.get("status", STATUS_NEW)]
                event_attributes["event_class"] = str( event_attributes["event_class"] )
                evtproxy = TransformEvent(**event_attributes)
                # translate actor to device/component/service
                self.getIdentifiersForUuids(event)
                self.extractActorElements(event, evtproxy)
                evtproxy.mark()

                transformer = EventTransformer(self, evtproxy, 
                                               evtFields=[f.name for f in RawEvent.DESCRIPTOR.fields],
                                               reqdEvtFields=evtdetails["_REQUIRED_FIELDS"],
                                               dedupEvtFields=evtdetails["_DEDUP_FIELDS"]
                                               )
                # run event thru identity and transforms
                log.debug("identify devices for event: %s", event.uuid)
                transformer.prepEvent()
                log.debug("Event attributes updated (prepEvent): %s", evtproxy.get_changes())
                if "status" in evtproxy.get_changes():
                    if evtproxy.get_changes()["status"] == "drop":
                        log.debug("dropped event after identify: %s", event.uuid);
                        return

                # add clearClasses sent in with event
                evtproxy._clearClasses.extend(evtdetails[CLEAR_CLASSES])
                evtproxy.freeze()

                log.debug("invoke transforms on event: %s", event.uuid)
                transformer.transformEvent()
                log.debug("Event attributes updated (transformEvent): %s", evtproxy.get_changes())
                if "status" in evtproxy.get_changes():
                    if evtproxy.get_changes()["status"] == "drop":
                        log.debug("dropped event after transforms: %s", event.uuid);
                        return

                # if status was updated in transform, map back to enum for storage in outbound event
                if "status" in evtproxy.get_changes():
                    if evtproxy.status in statusConvertToEnum:
                        evtproxy.status = statusConvertToEnum[evtproxy.status]
                    else:
                        log.warning("invalid event state '%s' set in transform", evtproxy.status)
                        return

                # copy adapter changes back to event attribs and details
                stdFields = set(f.name for f in RawEvent.DESCRIPTOR.fields)
                for (attr,val) in evtproxy.get_changes().items():
                    if attr in stdFields:
                        setattr(event, attr, val)
                    elif attr in "service device component".split():
                        # update actor uuids/identifiers - skip these for now
                        pass
                    elif attr in "status _clearClasses".split():
                        # skip these now, we'll always copy into output whether changed or not
                        pass
                    else:
                        # copy extra attributes to details
                        evtdetails[attr] = val

                # fix up any service/device/component refs and get uuids
                self.updateActorReferences(event, evtproxy.get_changes())

                # set zepevent control fields
                zepevent.clear_event_class.extend(list(set(evtproxy._clearClasses)))
                zepevent.status = evtproxy.status

                # strip off details used internally
                self.removeEventControlDetails(event, evtdetails)

            # convert event details dict back to event details name-values
            self.eventDetailDictToNameValues(event, evtdetails)

            # add event index tags for fast event retrieval
            self.addEventIndexTerms(event.actor, zepevent.tags, event.details)

            # Apply any event plugins
            for name, plugin in getUtilitiesFor(IEventPlugin):
                try:
                    plugin.apply(zepevent, self.dmd)
                except Exception, e:
                    log.exception('Event plugin %s encountered an error; skipping.' % name)
                    continue

            # forward event to output queue
            yield self.publishEvent(zepevent)
            log.debug("published event: %s", event.uuid);
            self.logEvent(log.debug, event, evtdetails)

        finally:
            # all done, ack message
            yield self.queueConsumer.acknowledge(message)

    def logEvent(self, logfn, event, details):
        statusdata = dict((f.name,getattr(event,f.name,None)) for f in RawEvent.DESCRIPTOR.fields)
        logfn("Event info: %s", statusdata)
        if details:
            logfn("Detail data: %s", details)

    def getFieldList(self):
        return [f.name for f in RawEvent.DESCRIPTOR.fields]
 
    def getDmd(self):
        return self.dmd

class ZenEventD(ZCmdBase):
    def run(self):
        task = ProcessEventMessageTask()
        self._consumer = QueueConsumer(task,self.dmd)
        if self.options.cycle:
            reactor.callWhenRunning(self._start)
            reactor.run()
        else:
            log.info('Shutting down: use cycle option ')


    def _start(self):
        log.info('starting queue consumer task')
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()


    @defer.inlineCallbacks
    def _shutdown(self, *ignored):
        if self._consumer:
            yield self._consumer.shutdown()
        try:
            reactor.stop()
        except ReactorNotRunning:
            pass

if __name__ == '__main__':
    zed = ZenEventD()
    zed.run()

