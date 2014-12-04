##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import signal
import socket
import time
import os

from amqplib.client_0_8.exceptions import AMQPConnectionException
from zope.component import getUtility
from Products.ZenEvents.zeneventd import BaseQueueConsumerTask, EventPipelineProcessor
from Products.ZenEvents.zeneventd import QUEUE_RAW_ZEN_EVENTS
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.jsonformat import to_dict
from zenoss.protocols.eventlet.amqp import Publishable, getProtobufPubSub
from Products.ZenCollector.utils.workers import workersBuildOptions
from zope.component.event import objectEventNotify
from Products.ZenEvents.daemonlifecycle import BuildOptionsEvent

log = logging.getLogger("zen.eventd.worker")


class EventletQueueConsumerTask(BaseQueueConsumerTask, BasePubSubMessageTask):

    def __init__(self, processor):
        BaseQueueConsumerTask.__init__(self, processor)

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        zepRawEvent = self.processor.processMessage(message)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("[pid %s] Publishing event: %s", os.getpid(), to_dict(zepRawEvent))

        yield Publishable(zepRawEvent, exchange=self._dest_exchange,
                          routingKey=self._routing_key(zepRawEvent))


class EventDEventletWorker(ZCmdBase):

    def __init__(self):
        super(EventDEventletWorker, self).__init__()
        self._amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        self._queueSchema = getUtility(IQueueSchema)

    # ZEN-15338: correctErrors, warnErrors to False to stop options from being commented out earlier
    def getConfigFileDefaults(self, filename, correctErrors=False, warnErrors=False):
        return super(EventDEventletWorker, self).getConfigFileDefaults(
            filename, correctErrors=correctErrors)

    # ZEN-15338: correctErrors, warnErrors to False to stop options from being commented out earlier
    def validateConfigFile(self, filename, lines, correctErrors=False, warnErrors=False):
        return super(EventDEventletWorker, self).validateConfigFile(
            filename, lines, correctErrors=correctErrors, warnErrors=warnErrors)

    def run(self):
        self._shutdown = False
        signal.signal(signal.SIGTERM, self._sigterm)
        log.info("[pid %s] Zeneventd worker starting...", os.getpid())
        task = EventletQueueConsumerTask(EventPipelineProcessor(self.dmd))
        self._listen(task)

    def shutdown(self):
        self._shutdown = True
        if self._pubsub:
            self._pubsub.shutdown()
            self._pubsub = None

    def buildOptions(self):
        # ZEN-15338: Move parser options into zeneventdEvents.py
        #  * Add all future parser options to zeneventdEvents.py
        super(EventDEventletWorker, self).buildOptions()
        objectEventNotify(BuildOptionsEvent(self))

    def _sigterm(self, signum=None, frame=None):
        log.debug("[pid %s] Worker sigterm...", os.getpid())
        self.shutdown()

    def _listen(self, task, retry_wait=30):
        self._pubsub = None
        keepTrying = True
        sleep = 0
        while keepTrying and not self._shutdown:
            try:
                if sleep:
                    log.info("[pid %s] Waiting %s seconds to reconnect...", os.getpid(), sleep)
                    time.sleep(sleep)
                    sleep = min(retry_wait, sleep * 2)
                else:
                    sleep = .1
                log.info("[pid %s] Connecting to RabbitMQ...", os.getpid())
                self._pubsub = getProtobufPubSub(self._amqpConnectionInfo, self._queueSchema, QUEUE_RAW_ZEN_EVENTS)
                self._pubsub.registerHandler('$Event', task)
                self._pubsub.registerExchange('$ZepZenEvents')
                self._pubsub.messagesPerWorker = self.options.messagesPerWorker
                # reset sleep time
                sleep = 0
                self._pubsub.run()
            except (socket.error, AMQPConnectionException) as e:
                log.warn("[pid %s] RabbitMQ Connection error %s", os.getpid(), e)
            except KeyboardInterrupt:
                keepTrying = False
            finally:
                if self._pubsub:
                    self._pubsub.shutdown()
                    self._pubsub = None
