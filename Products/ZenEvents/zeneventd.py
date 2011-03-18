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
import os
import signal
import multiprocessing

import Globals
from zope.component import getUtilitiesFor
from zope.interface import implements

from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.ZenDaemon import ZenDaemon
from zenoss.protocols import queueschema
from zenoss.protocols.eventlet.amqp import getProtobufPubSub
from zenoss.protocols.protobufs.zep_pb2 import ZepRawEvent
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_NEW,
    STATUS_ACKNOWLEDGED,
    STATUS_SUPPRESSED,
    STATUS_CLOSED,
    STATUS_CLEARED,
    STATUS_DROPPED,
    STATUS_AGED)
from zenoss.protocols.eventlet.amqp import Publishable
from zenoss.protocols.jsonformat import to_dict
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenEvents.events2.processing import *

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

    def __init__(self, dmd):
        self.dmd = dmd
        self.dest_routing_key_prefix = 'zenoss.zenevent'

        self._dest_exchange = queueschema.getExchange("$ZepZenEvents")
        #self._eventPlugins = getUtilitiesFor(IEventPlugin)
        self._manager = Manager(self.dmd)
        self._pipes = (
            EventPluginPipe(self._manager, IPreEventPlugin),
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextPipe(self._manager),
            FingerprintPipe(self._manager, 'FingerprintPipe_1'),
            TransformPipe(self._manager),
            # See if we need to update after a transform
            IdentifierPipe(self._manager),
            AddDeviceContextPipe(self._manager),
            FingerprintPipe(self._manager, 'FingerprintPipe_2'),
            SerializeContextPipe(self._manager),
            EventPluginPipe(self._manager, IPostEventPlugin),
            ClearClassRefreshPipe(self._manager),
            EventTagPipe(self._manager),
        )

    def _routing_key(self, event):
        return (self.dest_routing_key_prefix +
                event.raw_event.event_class.replace('/', '.').lower())

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        self.dmd._p_jar.sync()
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

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Publishing event: %s", to_dict(eventContext.zepRawEvent))

        yield Publishable(eventContext.zepRawEvent,
                          exchange=self._dest_exchange,
                          routingKey=self._routing_key(
                              eventContext.zepRawEvent))


class EventDWorker(ZCmdBase):

    def run(self):
        task = ProcessEventMessageTask(self.dmd)
        self._pubsub = getProtobufPubSub('$RawZenEvents')
        self._pubsub.registerHandler('$RawEvent', task)
        self._pubsub.registerExchange('$ZepZenEvents')
        try:
            self._pubsub.run()
        except KeyboardInterrupt:
            pass
        finally:
            self._pubsub.shutdown()

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
        log.info("Shutting down: %s" % (name,))


class ZenEventD(ZenDaemon):

    def __init__(self, *args, **kwargs):
        super(ZenEventD, self).__init__(*args, **kwargs)
        self._workers = []

    def sigterm(self, signum=None, frame=None):
        log.info("Shutting down...")
        for worker in self._workers:
            os.kill(worker.pid, signal.SIGTERM)
            worker.join(0.5)
            worker.terminate()

    def sighandler_USR1(self, signum, frame):
        super(ZenEventD, self).sighandler_USR1(signum, frame)
        for worker in self._workers:
            os.kill(worker.pid, signal.SIGUSR1)

    def run(self):
        if self.options.daemon and self.options.workers > 1:
            numworkers = self.options.workers
            pid = multiprocessing.current_process().pid
            log.info("Starting event daemon (pid %s)" % pid)
            for i in range(numworkers):
                p = multiprocessing.Process(
                    target=run_worker,
                    name='Event worker %s' % (i+1))
                p.start()
                self._workers.append(p)
            signal.signal(signal.SIGTERM, self.sigterm)
            for worker in self._workers:
                worker.join()
        else:
            EventDWorker().run()

    def buildOptions(self):
        super(ZenEventD, self).buildOptions()
        self.parser.add_option('--workers',
                    type="int",
                    default=2,
                    help="The number of event processing workers to run "
                         "(ignored when running in the foreground)")
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



if __name__ == '__main__':
    zed = ZenEventD()
    zed.run()

