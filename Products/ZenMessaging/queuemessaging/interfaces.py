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
from zope.interface import Interface


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
        @param routing_key: Key by which consumers will setup the queus to route
        @type  message: string or Protobuff
        @param message: message we are sending in the queue
        """

class IProtobufSerializer(Interface):
    """
    Interfaces fro converting a Zope object to a protobuf.
    """

    def fill(protobuf):
        """
        This takes a protobuf and applies the properties from our zope object.
        @type  protobuf: Protobuf Message Object
        @param protobuf: The object we are populating
        @rtype:   protobuf
        @return:  The same protobuf passed in but with its properties set
        """


