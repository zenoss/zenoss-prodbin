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
from twisted.internet.error import ReactorNotRunning

import os
import signal
import multiprocessing
import time
import socket
import sys
from datetime import datetime, timedelta

import Globals
from zope.component import getUtilitiesFor
from zope.interface import implements

from amqplib.client_0_8.exceptions import AMQPConnectionException
from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.guid import guid
from zenoss.protocols import queueschema
from zenoss.protocols.eventlet.amqp import getProtobufPubSub
from zenoss.protocols.protobufs.zep_pb2 import ZepRawEvent, RawEvent
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_SUPPRESSED,
    STATUS_CLOSED,
    STATUS_CLEARED,
    STATUS_DROPPED,
    STATUS_AGED)
from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import to_dict, from_dict
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenEvents.events2.processing import *
from Products.ZenCollector.utils.workers import ProcessWorkers, workersBuildOptions
from Products.ZenEvents.interfaces import IPreEventPlugin, IPostEventPlugin

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

    SYNC_EVERY_EVENT = False

    def __init__(self, dmd):
        self.dmd = dmd
        self.dest_routing_key_prefix = 'zenoss.zenevent'

        self._dest_exchange = queueschema.getExchange("$ZepZenEvents")
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
                event.raw_event.event_class.replace('/', '.').lower())

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
                    zepevent.raw_event.CopyFrom(message)
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("Received event: %s", to_dict(zepevent.raw_event))

                    eventContext = EventContext(log, zepevent)

                    for pipe in self._pipes:
                        eventContext = pipe(eventContext)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug('After pipe %s, event context is %s' % ( pipe, eventContext ))
                        if eventContext.zepRawEvent.status == STATUS_DROPPED:
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
            log.info("Failed to process event, forward original raw event: %s", to_dict(zepevent.raw_event))
            log.exception(e)

            # construct wrapper event to report this event processing failure (including content of the
            # original event)
            origzepevent = ZepRawEvent()
            origzepevent.raw_event.CopyFrom(message)
            failReportEvent = dict(
                uuid = guid.generate(),
                created_time = int(time.time()*1000),
                fingerprint='|'.join(['zeneventd', 'processMessage', repr(e)]),
                # Don't send the *same* event class or we trash and and crash endlessly
                eventClass='/',
                summary='Internal exception processing event: %r' % e,
                message='Internal exception processing event: %r/%s' % (e, to_dict(origzepevent.raw_event)),
                severity=4,
            )
            zepevent = ZepRawEvent()
            zepevent.raw_event.CopyFrom(from_dict(RawEvent, failReportEvent))
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
                self._pubsub = getProtobufPubSub('$RawZenEvents')
                self._pubsub.registerHandler('$RawEvent', task)
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
        self.parser.add_option('--workers',
                    type="int",
                    default=2,
                    help="The number of event processing workers to run "
                         "(ignored when running in the foreground)")

    def parseOptions(self):
        """
        Don't ever allow a worker to be a daemon
        """
        super(EventDWorker, self).parseOptions()
        self.options.daemon = False


def run_worker():
    name = multiprocessing.current_process().name
    pid = multiprocessing.current_process().pid
    log.info("Starting: %s (pid %s)" % (name, pid))
    try:
        worker = EventDWorker()
        worker.run()
    finally:
        log.debug("Shutting down: %s" % (name,))


class ZenEventD(ZenDaemon):

    def __init__(self, *args, **kwargs):
        super(ZenEventD, self).__init__(*args, **kwargs)
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                     'zeneventd',
                                                     self.options.maintenancecycle *3)
        self._workers = ProcessWorkers(self.options.workers, run_worker,
                                       "Event worker")
        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                  self._heartbeatSender)

    def _shutdown(self, *ignored):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        self._workers.shutdown()

    def run(self):
        ProcessEventMessageTask.SYNC_EVERY_EVENT = self.options.syncEveryEvent

        if self.options.daemon:
            reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
            self._workers.startWorkers()
            self._maintenanceCycle.start()
            reactor.run()

        else:
            EventDWorker().run()

    def buildOptions(self):
        super(ZenEventD, self).buildOptions()

        workersBuildOptions(self.parser, default=2)
        maintenanceBuildOptions(self.parser)
        # Have to add in all the ZCmdBase options because they get passed
        # through to the workers but will be invalid if not allowed here
        self.parser.add_option('-R', '--dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")
        self.parser.add_option('--cachesize',
                    dest="cachesize",default=1000, type='int',
                    help="in memory cachesize default: 1000")
        self.parser.add_option('--host',
                    dest="host",default="localhost",
                    help="hostname of MySQL object store")
        self.parser.add_option('--port',
                    dest="port", type="int", default=3306,
                    help="port of MySQL object store")
        self.parser.add_option('--mysqluser', dest='mysqluser', default='zenoss',
                    help='username for MySQL object store')
        self.parser.add_option('--mysqlpasswd', dest='mysqlpasswd', default='zenoss',
                    help='passwd for MySQL object store')
        self.parser.add_option('--mysqldb', dest='mysqldb', default='zodb',
                    help='Name of database for MySQL object store')
        self.parser.add_option('--cacheservers', dest='cacheservers', default="",
                    help='memcached servers to use for object cache (eg. 127.0.0.1:11211)')
        self.parser.add_option('--poll-interval', dest='pollinterval', default=None, type='int',
                    help='Defer polling the database for the specified maximum time interval, in seconds.'
                    ' This will default to 60 only if --cacheservers is set.')
        self.parser.add_option('--synceveryevent', dest='syncEveryEvent',
                    action="store_true", default=False,
                    help='Force sync() before processing every event; default is to sync() no more often '
                    'than once every 1/2 second.')



if __name__ == '__main__':
    zed = ZenEventD()
    zed.run()

