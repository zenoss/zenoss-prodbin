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
import Globals

from Acquisition import aq_chain
from zope.component import getUtilitiesFor
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from zenoss.protocols import queueschema
from zenoss.protocols.protobufs.zep_pb2 import RawEvent, ZepRawEvent
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_CLEAR
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_SUPPRESSED,
    STATUS_CLOSED,
    STATUS_CLEARED,
    STATUS_DROPPED,
    STATUS_AGED)
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT, SERVICE
from zenoss.protocols.eventlet.amqp import getProtobufPubSub
from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import to_dict
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenEvents.events2.processing import *

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
    "new": STATUS_NEW,
    "ack": STATUS_ACKNOWLEDGED,
    "suppressed": STATUS_SUPPRESSED,
    "closed": STATUS_CLOSED,
    "cleared": STATUS_CLEARED,
    "dropped": STATUS_DROPPED,
    "aged": STATUS_AGED,
}
statusConvertToString = dict((v, k) for k, v in statusConvertToEnum.items())

# add for legacy compatibility
statusConvertToEnum['status'] = STATUS_NEW
statusConvertToEnum['history'] = STATUS_CLOSED
statusConvertToEnum['drop'] = STATUS_DROPPED


class ProcessEventMessageTask(BasePubSubMessageTask):

    implements(IQueueConsumerTask)

    def __init__(self, dmd):
        self.dmd = dmd
        self.dest_routing_key_prefix = 'zenoss.zenevent'

        self._dest_exchange = queueschema.getExchange("$ZepZenEvents")
        self._eventPlugins = getUtilitiesFor(IEventPlugin)
        self._manager = Manager(self.dmd)
        self._pipes = (
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextPipe(self._manager),
            FingerprintPipe(self._manager),
            TransformPipe(self._manager),
            # See if we need to update after a transform
            IdentifierPipe(self._manager),
            AddDeviceContextPipe(self._manager),
            FingerprintPipe(self._manager),
            SerializeContextPipe(self._manager),
            EventPluginPipe(self._manager),
            EventTagPipe(self._manager),
        )

    def _routing_key(self, event):
        return (self.dest_routing_key_prefix +
                event.raw_event.event_class.replace('/', '.').lower())

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        self.dmd._p_jar.sync()
        # extract event from message body
        zepevent = ZepRawEvent()
        zepevent.raw_event.CopyFrom(message)
        if log.isEnabledFor(logging.DEBUG):
            log.debug("Received event: %s", to_dict(zepevent.raw_event))

        eventContext = EventContext(log, zepevent)

        for pipe in self._pipes:
            eventContext = pipe(eventContext)
            if eventContext.zepRawEvent.status == STATUS_DROPPED:
                raise DropEvent('Dropped by %s' % pipe, eventContext.event)
        yield Publishable(eventContext.zepRawEvent,
                          exchange=self._dest_exchange,
                          routingKey=self._routing_key(
                              eventContext.zepRawEvent))


class ZenEventD(ZCmdBase):
    def run(self):
        task = ProcessEventMessageTask(self.dmd)
        self._pubsub = getProtobufPubSub('$RawZenEvents')
        self._pubsub.registerHandler('$RawEvent', task)
        self._pubsub.registerExchange('$ZepZenEvents')

        try:
            self._pubsub.run()
        except KeyboardInterrupt:
            pass

        finally:
            log.info('Shutting down...')
            self._pubsub.shutdown()

if __name__ == '__main__':
    zed = ZenEventD()
    zed.run()
