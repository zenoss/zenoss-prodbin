###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import inspect
import logging
log = logging.getLogger("zen.AmqpPubSub")
from Products.ZenEvents.events2.processing import DropEvent, ProcessingException
from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import to_dict

class BasePubSubMessageTask(object):
    """
    Base for other eventlet-using queue consumers.

    Subclasses should implement the processMessage method, which can yield or
    return a tuple of (exchange, routing_key, protobuf) in order to publish its
    own messages.
    """
    def __call__(self, message, proto):
        try:
            result = self.processMessage(proto)

            if result:
                if not inspect.isgenerator(result):
                    result = (result,)

                for msg in result:
                    if isinstance(msg, Publishable):
                        yield msg
                    else:
                        exchange, routing_key, msg = result
                        yield Publishable(msg, exchange=exchange, routingKey=routing_key)

            message.ack()

        except DropEvent as e:
            log.warning('%s - %s' % (e.message, to_dict(e.event)))
            message.ack()

        except ProcessingException as e:
            log.error('%s - %s' % (e.message, to_dict(e.event)))
            log.exception(e)
            message.reject()

        except Exception as e:
            log.exception(e)
            message.reject()

    def processMessage(self, protobuf):
        raise NotImplementedError

