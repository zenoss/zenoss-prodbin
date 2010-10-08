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
from interfaces import IQueuePublisher


class AsyncQueuePublisher(object):
    """
    Sends the
    """
    implements(IQueuePublisher)

    def __init__(self):
        self._amqpClient = AMQPFactory()

    def publish(self, exchange, routing_key, message):
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
        self._amqpClient.send(exchange, routing_key, message)


class BlockingQueuePublisher(object):
    """
    Class that is responsible for sending messages to the amqp exchange.
    """

    def publish(self, exchange, routing_key, message):
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
        blockingpublish(exchange, routing_key, message)

