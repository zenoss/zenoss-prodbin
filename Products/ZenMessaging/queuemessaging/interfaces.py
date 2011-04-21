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
    def publish(exchange, routing_key, message, exchange_type):
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
    exchange = Attribute("The name of the exchange the task wants to listen to")
    routing_key = Attribute("The Routing Key used to bind the queue to the exchange")
    queue_name = Attribute("The name of the queue that this task will listen to.")
    exchange_type = Attribute("The type of exchange (topic, direct, fanout)")

    def processMessage(message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """

class IEventPublisher(Interface):
    """
    Publishes events.
    """
    def publish(event, mandatory=False):
        """
        Publish event to the raw event queue.
        """
