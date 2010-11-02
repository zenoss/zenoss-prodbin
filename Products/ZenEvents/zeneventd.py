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

# set up the zope environment
import Zope2
CONF_FILE = os.path.join(os.environ['ZENHOME'], 'etc', 'zope.conf')
Zope2.configure(CONF_FILE)

import logging

from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumerProcess
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask, IProtobufSerializer
from zenoss.protocols.protobufs.zep_pb2 import RawEvent as RawEventProtobuf
from zenoss.protocols.protobufs.zep_pb2 import Event as EventProtobuf
from zenoss.protocols.protobufs.zep_pb2 import EventSummary as EventSummaryProtobuf
from zenoss.protocols.amqpconfig import getAMQPConfiguration
#from twisted.internet import reactor, protocol, defer
from zope.interface import implements


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

        queue = config.getQueue("$RawZenEvents")
        binding = queue.getBinding("$RawZenEvents")
        self.exchange = binding.exchange.name
        self.routing_key = binding.routing_key
        self.exchange_type = binding.exchange.type
        self.queue_name = queue.name

        self.dest_exchange = config.getExchange("$ZepZenEvents")
        self.dest_routing_key_prefix = 'zenoss.zenevent'

    def identifyEvent(self, event):
        return event

    def transformEvent(self, event):
        return event

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
            # read message from queue - if terminating sentinel marker, return
            if message.content.body == self.queueConsumer.MARKER:
                log.info("Received MARKER sentinel, exiting message loop")
                return

            # extract raw event from message body
            rawevt = RawEventProtobuf()
            rawevt.ParseFromString(message.content.body)

            # populate event from raw event
            fields = """actor agent details event_class event_class_key event_group
                        event_key fingerprint message monitor nt_event_code severity
                        summary syslog_facility syslog_priority""".split()
            event = EventProtobuf()
            for f in fields:
               val = getattr(rawevt, f, None)
               setattr(event, f, val)

            # run event thru identity and transforms
            event = self.identifyEvent(event)
            event = self.transformEvent(event)

            eventsummary = EventSummaryProtobuf()
            eventsummary.occurences[0] = event

            # forward event to output queue
            self.publishEvent(eventsummary)

        finally:
            # all done, ack message
            self.queueConsumer.acknowledge(message)


if __name__ == '__main__':
    task = ProcessEventMessageTask()
    consumer = QueueConsumerProcess(task)
    options, args = consumer.server.parser.parse_args()
    logging.basicConfig(level=options.logseverity)
    consumer.run()
