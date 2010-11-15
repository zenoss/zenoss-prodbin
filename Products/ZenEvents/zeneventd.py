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

from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask, IProtobufSerializer
from Products.ZenUtils.ZCmdBase import ZCmdBase
from zenoss.protocols.protobufs.zep_pb2 import RawEvent, ZepRawEvent, EventDetail, EventIndex, EventActor, SEVERITY_CLEAR
from zenoss.protocols.protobufs.zep_pb2 import ACTION_NEW, ACTION_CLOSE, ACTION_DROP
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT, SERVICE
from zenoss.protocols.amqpconfig import getAMQPConfiguration
from twisted.internet import reactor, protocol, defer
from twisted.internet.error import ReactorNotRunning
from zope.interface import implements

from Products.ZenEvents.MySqlSendEvent import EventTransformer
TRANSFORM_EVENT_IN_EVENTD = True

from Products.ZenEvents.transformApi import Event as TransformEvent
from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenUtils.guid.interfaces import IGUIDManager, IGlobalIdentifier
from Products.Zuul.interfaces import ICatalogTool, IInfo
from Products.ZenModel.Device import Device
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.AdvancedQuery import Eq
from Products.ZenModel.DeviceClass import DeviceClass

import logging
log = logging.getLogger("zen.eventd")

# 'action' value mappings
actionConvertToOld = {
    "ACTION_NEW" : "status",
    "ACTION_CLOSE" : "history",
    "ACTION_DROP" : "drop",
    }
actionConvertToNew = dict((v,k) for k,v in actionConvertToOld.items())
actionConvertToEnum = {
    "ACTION_NEW" : ACTION_NEW,
    "ACTION_CLOSE" : ACTION_CLOSE,
    "ACTION_DROP" : ACTION_DROP,
    }

ACTION = "_ACTION"
CLEAR_CLASSES = "_CLEAR_CLASSES"


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
        if not ACTION in details or details[ACTION] is None:
            details[ACTION] = 'ACTION_NEW'

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
        for name in [ACTION, CLEAR_CLASSES,] + "_DEDUP_FIELDS _REQUIRED_FIELDS".split():
            if name in details:
                del details[name]

    def getObjectForUuid(self, uuid):
        gm = IGUIDManager(self.dmd)
        return gm.getObject(uuid)

    def getObjectUuid(self, objid, idattr, objcls, parentUuid=None):
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
            return IGlobalIdentifier(element).getGUID()

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
            uuid = self.getObjectUuid(identifier, 'id', cls, parentUuid)

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

    def getLocationUuid(self, locn):
        if locn is not None:
            return IGlobalIdentifier(locn).getGUID()
        else:
            return ''

    def addEventIndexTerms(self, event, evtindex):
        #indexattrs = [f.name for f in EventIndex.DESCRIPTOR.fields]
        """['device_id', 'device_title', 'device_priority', 
         'device_class_name_uuid', 'device_location_uuid', 'device_production_state', 
         'device_group_uuids', 'device_system_uuids', 'device_service_uuids', 
         'component_id', 'component_title', 'component_uuid', 'service_title', 
         'service_uuid']"""

        # extract device, component, and/or service from event actor uuid's
        elementrefs = { DEVICE : None, COMPONENT : None, SERVICE : None }
        for elementType in (DEVICE, COMPONENT, SERVICE):
            if event.actor.element_type_id == elementType and event.actor.element_uuid:
                elementrefs[elementType] = self.getObjectForUuid(event.actor.element_uuid)
            if event.actor.element_sub_type_id == elementType and event.actor.element_sub_uuid:
                elementrefs[elementType] = self.getObjectForUuid(event.actor.element_sub_uuid)

        # set device search terms
        device = elementrefs[DEVICE]
        if device is not None:
            attrs = "id title priority".split()
            for attr in attrs:
                attrval = getattr(device, attr, None)
                if attrval is not None:
                    setattr(evtindex, 'device_'+attr, attrval)
            evtindex.device_production_state = device.productionState
            evtindex.device_class_name_uuid = device.deviceClass().uuid
            evtindex.device_location_uuid = self.getLocationUuid(device.location())
            # TODO - get uuids for device groups, systems, and services

        # set component search terms
        component = elementrefs[COMPONENT]
        if component is not None:
            attrs = "id title uuid".split()
            for attr in attrs:
                attrval = getattr(service,attr,None)
                if attrval is not None:
                    setattr(evtindex, 'component_'+attr, attrval)

        # set service search terms
        service = elementrefs[SERVICE]
        if service  is not None:
            attrs = "uuid title".split()
            for attr in attrs:
                attrval = getattr(service,attr,None)
                if attrval is not None:
                    setattr(evtindex, 'service_'+attr, attrval)

    def publishEvent(self, event):
        self.queueConsumer.publishMessage("$ZepZenEvents", 
                                          self.dest_routing_key_prefix + 
                                              event.raw_event.event_class.replace('/','.').lower(),
                                          event)

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
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
                evtproxy = TransformEvent(**event_attributes)
                # translate actor to device/component/service
                self.getIdentifiersForUuids(event)
                self.extractActorElements(event, evtproxy)
                if evtdetails[ACTION] in actionConvertToOld:
                    evtproxy._action = actionConvertToOld[evtdetails[ACTION]]
                else:
                    evtproxy._action = actionConvertToOld["ACTION_NEW"]
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
                if "_action" in evtproxy.get_changes():
                    if evtproxy.get_changes()["_action"] == "drop":
                        log.debug("dropped event after identify: %s", event.uuid);
                        return

                # add clearClasses sent in with event
                evtproxy._clearClasses.extend(evtdetails[CLEAR_CLASSES])
                evtproxy.freeze()

                log.debug("invoke transforms on event: %s", event.uuid)
                transformer.transformEvent()
                log.debug("Event attributes updated (transformEvent): %s", evtproxy.get_changes())
                if "_action" in evtproxy.get_changes():
                    if evtproxy.get_changes()["_action"] == "drop":
                        log.debug("dropped event after transforms: %s", event.uuid);
                        return

                # copy adapter changes back to event attribs and details
                stdFields = set(f.name for f in RawEvent.DESCRIPTOR.fields)
                for (attr,val) in evtproxy.get_changes().items():
                    if attr in stdFields:
                        setattr(event, attr, val)
                    elif attr in "service device component".split():
                        # update actor uuids/identifiers - skip these for now
                        pass
                    elif attr in "_action _clearClasses".split():
                        # skip these now, we'll always copy into output whether changed or not
                        pass
                    else:
                        # copy extra attributes to details
                        evtdetails[attr] = val

                # fix up any service/device/component refs and get uuids
                self.updateActorReferences(event, evtproxy.get_changes())

                # set zepevent control fields
                zepevent.clear_event_class.extend(list(set(evtproxy._clearClasses)))
                zepevent.action = actionConvertToEnum[actionConvertToNew.get(evtproxy._action, ACTION_NEW)]

                # strip off details used internally
                self.removeEventControlDetails(event, evtdetails)

            # add event index tags for fast event retrieval
            log.debug("add index values for event: %s", event.uuid)
            self.addEventIndexTerms(event, zepevent.index)

            # convert event details dict back to event details name-values
            self.eventDetailDictToNameValues(event, evtdetails)

            # forward event to output queue
            self.publishEvent(zepevent)
            log.debug("published event: %s", event.uuid);
            self.logEvent(log.debug, event, evtdetails)

        finally:
            # all done, ack message
            self.queueConsumer.acknowledge(message)

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

