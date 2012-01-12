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
from twisted.internet import reactor

import signal
import time
import socket
from datetime import datetime, timedelta

import Globals
from zope.component import getUtility, adapter
from zope.interface import implements
from zope.component.event import objectEventNotify

from amqplib.client_0_8.exceptions import AMQPConnectionException
from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.guid import guid
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.eventlet.amqp import getProtobufPubSub
from zenoss.protocols.protobufs.zep_pb2 import ZepRawEvent, Event
from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import from_dict
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenEvents.events2.processing import *
from Products.ZenEvents.interfaces import IPreEventPlugin, IPostEventPlugin
from Products.ZenEvents.daemonlifecycle import DaemonCreatedEvent, SigTermEvent, SigUsr1Event
from Products.ZenEvents.daemonlifecycle import DaemonStartRunEvent, BuildOptionsEvent

import logging
log = logging.getLogger("zen.eventd")

class ProcessEventMessageTask(BasePubSubMessageTask):

    implements(IQueueConsumerTask)

    SYNC_EVERY_EVENT = False

    def __init__(self, dmd):
        self.dmd = dmd
        self._queueSchema = getUtility(IQueueSchema)
        self.dest_routing_key_prefix = 'zenoss.zenevent'

        self._dest_exchange = self._queueSchema.getExchange("$ZepZenEvents")
        self._manager = Manager(self.dmd)
        self._pipes = (
            EventPluginPipe(self._manager, IPreEventPlugin, 'PreEventPluginPipe'),
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextAndTagsPipe(self._manager),
            TransformAndReidentPipe(self._manager,
                TransformPipe(self._manager),
                [
                IdentifierPipe(self._manager),
                UpdateDeviceContextAndTagsPipe(self._manager),
                ]),
            AssignDefaultEventClassAndTagPipe(self._manager),
            FingerprintPipe(self._manager),
            SerializeContextPipe(self._manager),
            EventPluginPipe(self._manager, IPostEventPlugin, 'PostEventPluginPipe'),
            ClearClassRefreshPipe(self._manager),
        )

        if not self.SYNC_EVERY_EVENT:
            # don't call sync() more often than 1 every 0.5 sec - helps throughput
            # when receiving events in bursts
            self.nextSync = datetime.now()
            self.syncInterval = timedelta(0,0,500000)

    def _routing_key(self, event):
        return (self.dest_routing_key_prefix +
                event.event.event_class.replace('/', '.').lower())

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """

        if self.SYNC_EVERY_EVENT:
            doSync = True
        else:
            # sync() db if it has been longer than self.syncInterval since the last time
            currentTime = datetime.now()
            doSync = currentTime > self.nextSync
            self.nextSync = currentTime + self.syncInterval

        if doSync:
            self.dmd._p_jar.sync()

        try:
            retry = True
            processed = False
            while not processed:
                try:
                    # extract event from message body
                    zepevent = ZepRawEvent()
                    zepevent.event.CopyFrom(message)
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("Received event: %s", to_dict(zepevent.event))

                    eventContext = EventContext(log, zepevent)

                    for pipe in self._pipes:
                        eventContext = pipe(eventContext)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug('After pipe %s, event context is %s' % ( pipe.name, to_dict(eventContext.zepRawEvent) ))
                        if eventContext.event.status == STATUS_DROPPED:
                            raise DropEvent('Dropped by %s' % pipe, eventContext.event)

                    processed = True

                except AttributeError:
                    # _manager throws Attribute errors if connection to zope is lost - reset
                    # and retry ONE time
                    if retry:
                        retry=False
                        log.debug("Resetting connection to catalogs")
                        self._manager.reset()
                    else:
                        raise

        except DropEvent:
            # we want these to propagate out
            raise
        except Exception as e:
            log.info("Failed to process event, forward original raw event: %s", to_dict(zepevent.event))
            # Pipes and plugins may raise ProcessingException's for their own reasons - only log unexpected
            # exceptions of other type (will insert stack trace in log)
            if not isinstance(e, ProcessingException):
                log.exception(e)

            # construct wrapper event to report this event processing failure (including content of the
            # original event)
            origzepevent = ZepRawEvent()
            origzepevent.event.CopyFrom(message)
            failReportEvent = dict(
                uuid = guid.generate(),
                created_time = int(time.time()*1000),
                fingerprint='|'.join(['zeneventd', 'processMessage', repr(e)]),
                # Don't send the *same* event class or we trash and and crash endlessly
                eventClass='/',
                summary='Internal exception processing event: %r' % e,
                message='Internal exception processing event: %r/%s' % (e, to_dict(origzepevent.event)),
                severity=4,
            )
            zepevent = ZepRawEvent()
            zepevent.event.CopyFrom(from_dict(Event, failReportEvent))
            eventContext = EventContext(log, zepevent)
            eventContext.eventProxy.device = 'zeneventd'
            eventContext.eventProxy.component = 'processMessage'

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Publishing event: %s", to_dict(eventContext.zepRawEvent))

        yield Publishable(eventContext.zepRawEvent,
                          exchange=self._dest_exchange,
                          routingKey=self._routing_key(
                              eventContext.zepRawEvent))


class EventDWorker(ZCmdBase):

    def __init__(self):
        super(EventDWorker, self).__init__()
        self._amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        self._queueSchema = getUtility(IQueueSchema)

    def run(self):
        self._shutdown = False
        signal.signal(signal.SIGTERM, self._sigterm)
        task = ProcessEventMessageTask(self.dmd)
        self._listen(task)

    def shutdown(self):
        self._shutdown = True
        if self._pubsub:
            self._pubsub.shutdown()
            self._pubsub = None

    def _sigterm(self, signum=None, frame=None):
        log.debug("worker sigterm...")
        self.shutdown()
        
    def _listen(self, task, retry_wait=30):
        self._pubsub = None
        keepTrying = True
        sleep = 0
        while keepTrying and not self._shutdown:
            try:
                if sleep:
                    log.info("Waiting %s seconds to reconnect..." % sleep)
                    time.sleep(sleep)
                    sleep = min(retry_wait, sleep * 2)
                else:
                    sleep = .1
                log.info("Connecting to RabbitMQ...")
                self._pubsub = getProtobufPubSub(self._amqpConnectionInfo, self._queueSchema, '$RawZenEvents')
                self._pubsub.registerHandler('$Event', task)
                self._pubsub.registerExchange('$ZepZenEvents')
                #reset sleep time
                sleep=0
                self._pubsub.run()
            except (socket.error, AMQPConnectionException) as e:
                log.warn("RabbitMQ Connection error %s" % e)
            except KeyboardInterrupt:
                keepTrying = False
            finally:
                if self._pubsub:
                    self._pubsub.shutdown()
                    self._pubsub = None

    def buildOptions(self):
        super(EventDWorker, self).buildOptions()
        objectEventNotify(BuildOptionsEvent(self))

    def parseOptions(self):
        """
        Don't ever allow a processor to be a daemon
        """
        super(EventDWorker, self).parseOptions()
        self.options.daemon = False


class ZenEventD(ZenDaemon):

    def __init__(self, *args, **kwargs):
        from Products.Five import zcml
        import Products.ZenossStartup
        zcml.load_site()
        super(ZenEventD, self).__init__(*args, **kwargs)
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                     'zeneventd',
                                                     self.options.maintenancecycle *3)
        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                  self._heartbeatSender)
        objectEventNotify(DaemonCreatedEvent(self))

    def _shutdown(self, *ignored):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        objectEventNotify(SigTermEvent(self))

    def run(self):
        ProcessEventMessageTask.SYNC_EVERY_EVENT = self.options.syncEveryEvent

        if self.options.daemon:
            reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
            self._maintenanceCycle.start()
            objectEventNotify(DaemonStartRunEvent(self))
        else:
            EventDWorker().run()

    def _sigUSR1_called(self, signum, frame):
        log.debug('_sigUSR1_called %s' % signum)
        objectEventNotify(SigUsr1Event(self, signum))

    def buildOptions(self):
        super(ZenEventD, self).buildOptions()
        maintenanceBuildOptions(self.parser)
        from zope.component import getUtility
        from Products.ZenUtils.ZodbFactory import IZodbFactoryLookup
        connectionFactory = getUtility(IZodbFactoryLookup).get()
        connectionFactory.buildOptions(self.parser)
        self.parser.add_option('--synceveryevent', dest='syncEveryEvent',
                    action="store_true", default=False,
                    help='Force sync() before processing every event; default is to sync() no more often '
                    'than once every 1/2 second.')
        objectEventNotify(BuildOptionsEvent(self))


@adapter(ZenEventD, DaemonStartRunEvent)
def onDaemonStartRun(daemon, event):
    """
    Start up an EventDWorker.
    """
    EventDWorker().run()

if __name__ == '__main__':
    # explicit import of ZenEventD to activate enterprise extensions
    from Products.ZenEvents.zeneventd import ZenEventD
    zed = ZenEventD()
    zed.run()

