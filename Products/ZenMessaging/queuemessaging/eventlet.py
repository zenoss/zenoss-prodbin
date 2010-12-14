import inspect
import logging
log = logging.getLogger("zen.AmqpPubSub")
from zenoss.protocols.eventlet.amqp import Publishable

class BasePubSubMessageTask(object):
    """
    Base for other eventlet-using queue consumers.

    Subclasses should implement the processMessage method, which can yield or
    return a tuple of (exchange, routing_key, protobuf) in order to publish its
    own messages.
    """
    def __call__(self, message, proto, acker):
        try:
            result = self.processMessage(proto)

            if result:
                if not inspect.isgenerator(result):
                    result = (result,)

                for message in result:
                    if isinstance(message, Publishable):
                        yield message
                    else:
                        exchange, routing_key, message = result
                        yield Publishable(message, exchange=exchange, routingKey=routing_key)

            acker()

        except Exception as e:
            log.exception(e)

    def processMessage(self, protobuf):
        raise NotImplementedError

