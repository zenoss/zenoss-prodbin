###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Interface, Attribute


class IQueuePublisher(Interface):
    """
    Interface for publishing to a queue
    """
    def publish(exchange, routing_key, message, createQueues=None, mandatory=False, immediate=False):
        """
        Publishes a message to an exchange. If twisted is running
        this will use the twisted amqp library, otherwise it will
        be blocking.
        @type  exchange: string
        @param exchange: destination exchange for the amqp server
        @type  routing_key: string
        @param routing_key: Key by which consumers will setup the queues to route
        @type  message: string or Protobuf
        @param message: message we are sending in the queue
        @type  createQueues: list
        @param createQueues: The name of the queues defined in the queue schema to create prior to
                             publishing the message.
        @type  mandatory: Boolean.
        @param mandatory: If true, will raise NoRouteException if there is no
                          destination queue for the published event.
        @type  immediate: Boolean
        @param immediate: If true, will raise NoConsumersException if there are
                          no active consumers for the published event (the event
                          is still sent to the queue).
        @raise zenoss.protocols.exceptions.NoRouteException: If mandatory is
               True and the message cannot be sent to a queue (the message is
               lost).
        @raise zenoss.protocols.exceptions.NoConsumersException: If immediate
               is True and the message is successfully sent to the queue but
               there are no active consumers to process the message.
        """

    channel = Attribute("Retrieves the connection to the queue")

class IProtobufSerializer(Interface):
    """
    Interfaces for converting a Zope object to a protobuf.
    """

    def fill(protobuf):
        """
        This takes a protobuf and applies the properties from our zope object.
        @type  protobuf: Protobuf Message Object
        @param protobuf: The object we are populating
        @rtype:   protobuf
        @return:  The same protobuf passed in but with its properties set
        """

class IModelProtobufSerializer(IProtobufSerializer):
    """
    Interfaces for converting a Zenoss model object to a Model protobuf.
    """
    modelType = Attribute("the model type for the object")
    

class IQueueConsumerTask(Interface):
    """
    A Task that is called once for every message that comes from the Queue. It is
    up to the task to acknowledge that message.
    """

    queueConsumer = Attribute("The consumer this task is proceessing a message for")
    queue = Attribute("The queue this queue will consume from.")

    def processMessage(message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """

class IEventPublisher(Interface):
    """
    Publishes events.
    """
    def publish(event, mandatory=False, immediate=False):
        """
        Publish event to the raw event queue.

        @type  event: Products.ZenEvents.Event
        @param event: The event to be published to the queue.
        @type  mandatory: Boolean.
        @param mandatory: If true, will raise NoRouteException if there is no
                          destination queue for the published event.
        @type  immediate: Boolean
        @param immediate: If true, will raise NoConsumersException if there are
                          no active consumers for the published event (the event
                          is still sent to the queue).
        @raise zenoss.protocols.exceptions.NoRouteException: If mandatory is
               True and the message cannot be sent to a queue (the message is
               lost).
        @raise zenoss.protocols.exceptions.NoConsumersException: If immediate
               is True and the message is successfully sent to the queue but
               there are no active consumers to process the message.
        """

    def close():
        """
        Closes the event publisher.
        """
