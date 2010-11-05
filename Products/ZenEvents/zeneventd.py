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
from zenoss.protocols.protobufs.zep_pb2 import RawEvent, EventDetail, EventIndex, EventActor, SEVERITY_CLEAR
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT, SERVICE
from zenoss.protocols.amqpconfig import getAMQPConfiguration
from twisted.internet import reactor, protocol, defer
from twisted.internet.error import ReactorNotRunning
from zope.interface import implements

TRANSFORM_EVENT_IN_EVENTD = False
if TRANSFORM_EVENT_IN_EVENTD:
    from Products.ZenEvents.MySqlSendEvent import EventTransformer
    from Products.ZenEvents.transformApi import Event as TransformEvent

import logging
log = logging.getLogger("zen.eventd")


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
        self.defaultEventId = "/Unknown"

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
        details["_ACTION"] = 'ACTION_NEW'
        details["_CLEAR_CLASSES"] = []
        if event.severity == SEVERITY_CLEAR and event.event_class:
            details["_CLEAR_CLASSES"].append(event.event_class)

    def getIdentifiersForUuids(self, evtproto, event):
        # translate uuids to identifiers, if not provided
        
        pass

    def extractActorElements(self, evtproto, event):
        if evtproto.actor.element_type_id == DEVICE:
            event.device = evtproto.actor.element_identifier
        elif evtproto.actor.element_type_id == COMPONENT:
            event.device = evtproto.actor.element_identifier
            event.component = evtproto.actor.element_sub_identifier
        elif evtproto.actor.element_type_id == SERVICE:
            event.service = evtproto.actor.element_identifier
            event.device = evtproto.actor.element_sub_identifier
        else:
            log.error("Unknown event actor type: %d", evtproto.actor.element_type_id)

    def addEventIndexTerms(self, event, details):
        # add search terms for this event
        #indexattrs = [f.name for f in EventIndex.DESCRIPTOR.fields]
        """['device_id', 'device_title', 'device_priority', 'device_ip_address', 
         'device_class_name_uuid', 'device_location_uuid', 'device_production_state', 
         'device_group_uuids', 'device_system_uuids', 'device_service_uuids', 
         'component_id', 'component_title', 'component_uuid', 'service_title', 
         'service_uuid']"""
        if event.actor.element_type_id == DEVICE:
            event.index.device_uuid = event.actor.element_uuid
        elif event.actor.element_type_id == COMPONENT:
            event.index.device_uuid = event.actor.element_uuid
            event.index.component_uuid = event.actor.sub_element_uuid
        elif event.actor.element_type_id == SERVICE:
            event.index.service_uuid = event.actor.element_uuid
            event.index.device_uuid = event.actor.sub_element_uuid
        else:
            log.error("Unknown event actor type: %d", event.actor.element_type_id)


    def publishEvent(self, event):
        self.queueConsumer.publishMessage(self.dest_exchange.name, 
                                          self.dest_routing_key_prefix + 
                                              event.event_class.replace('/','.'),
                                          event, 
                                          self.dest_exchange.type)

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
            event = RawEvent()
            event.ParseFromString(message.content.body)
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
                self.getIdentifiersForUuids(event, evtproxy)
                self.extractActorElements(event, evtproxy)
                evtproxy.action = evtdetails["_ACTION"]
                evtproxy.freeze()
                evtproxy.mark()

                transformer = EventTransformer(self, evtproxy)
                # run event thru identity and transforms
                log.debug("identify event devices: %s", event.uuid)
                transformer.prepEvent()
                if "action" in evtproxy.get_changes():
                    evtdetails["_ACTION"] = "ACTION_" + evtproxy.get_changes()["action"].upper()

                if evtdetails["_ACTION"].upper() == "ACTION_DROP":
                    log.debug("dropped event after identify: %s", event.uuid);
                    return

                log.debug("invoke transforms on event: %s", event.uuid)
                transformer.transformEvent()
                if "action" in evtproxy.get_changes():
                    evtdetails["_ACTION"] = "ACTION_" + evtproxy.get_changes()["action"].upper()

                if evtdetails["_ACTION"].upper() == "ACTION_DROP":
                    log.debug("dropped event after transforms: %s", event.uuid);
                    return

                # copy adapter changes back to event attribs and details
                stdFields = set(f.name for f in RawEvent.DESCRIPTOR.fields)
                log.debug("Event attributes updated: %s", evtproxy.get_changes())
                for (attr,val) in evtproxy.get_changes().items():
                    if attr in stdFields:
                        setattr(event, attr, val)
                    else:
                        if attr in "service device component".split():
                            # TODO - udpate actor uuids/identifiers
                            pass
                        else:
                            # TODO - copy extra attributes to details
                            pass

            # add event index tags for fast event retrieval
            log.debug("add index values for event: %s", event.uuid)
            self.addEventIndexTerms(event, evtdetails)

            # convert event details dict back to event details name-values
            self.eventDetailDictToNameValues(event, evtdetails)

            # forward event to output queue
            self.publishEvent(event)
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

class ZenEventD(object):
    def run(self):
        task = ProcessEventMessageTask()
        self._consumer = QueueConsumer(task)
        if self._consumer.options.cycle:
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

