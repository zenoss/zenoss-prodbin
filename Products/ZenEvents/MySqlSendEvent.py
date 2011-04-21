###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """MySqlSendEvent
Populate the events database with incoming events
"""

import threading
from Queue import Queue, Empty
import logging
log = logging.getLogger("zen.Events")

from zope.component import getUtility

import Products.ZenUtils.guid as guid
from Event import buildEventFromDict
from ZenEventClasses import Heartbeat, Unknown
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher, IQueuePublisher
from zenoss.protocols.protobufs.zep_pb2 import DaemonHeartbeat

class MySqlSendEventMixin:
    """
    Mix-in class that takes a MySQL db connection and builds inserts that
    sends the event to the backend.
    """

    def sendEvent(self, event):
        """
        Send an event to the backend.

        @param event: an event
        @type event: Event class
        @return: event id or None
        @rtype: string
        """
        if log.isEnabledFor(logging.DEBUG):
            log.debug('%s%s%s' % ('=' * 15, '  incoming event  ', '=' * 15))
        if isinstance(event, dict):
            event = buildEventFromDict(event)

        if getattr(event, 'eventClass', Unknown) == Heartbeat:
            log.debug("Got a %s %s heartbeat event (timeout %s sec).",
                      getattr(event, 'device', 'Unknown'),
                      getattr(event, 'component', 'Unknown'),
                      getattr(event, 'timeout', 'Unknown'))
            return self._sendHeartbeat(event)

        event.evid = guid.generate()
        self._publishEvent(event)
        return event.evid

    def _publishEvent(self, event):
        """
        Sends this event to the event fan out queue
        """
        publisher = getUtility(IEventPublisher)
        publisher.publish(event)

    def _sendHeartbeat(self, event):
        """
        Publishes a heartbeat message to the queue.

        @param event: event
        @type event: Event class
        """
        try:
            heartbeat = DaemonHeartbeat(monitor = event.device,
                                        daemon = getattr(event, "component", ""),
                                        timeout_seconds = int(event.timeout))
            publisher = getUtility(IQueuePublisher)
            publisher.publish('$Heartbeats', 'zenoss.heartbeat.%s' % heartbeat.monitor, heartbeat)
        except (ValueError, AttributeError) as e:
            log.error("Unable to send heartbeat: %s", event)
            log.exception(e)

class MySqlSendEvent(MySqlSendEventMixin):
    """
    Class that can connect to backend must be passed:
        username - backend username to use
        password - backend password
        database - backend database name
        host - hostname of database server
        port - port
    """
    backend = "mysql"

    copyattrs = (
        "username",
        "password",
        "database",
        "host",
        "port",
        "requiredEventFields",
        "defaultEventId",
        "statusTable",
        "deviceField",
        "componentField",
        "eventClassField",
        "firstTimeField",
        "lastTimeField",
        "countField",
        "detailTable",
    )

    def __init__(self, zem):
        for att in self.copyattrs:
            value = getattr(zem, att)
            setattr(self, att, value)
        self._fieldlist = zem.getFieldList()

    def stop(self):
        """
        To be implemented by the subclass
        """
        pass


    def getFieldList(self):
        """
        Return the list of fields

        @return: list of fields
        @rtype: list
        """
        return self._fieldlist


class MySqlSendEventThread(threading.Thread, MySqlSendEvent):
    """
    Wrapper around MySQL database connection
    """

    running = True

    def __init__(self, zem):
        threading.Thread.__init__(self)
        MySqlSendEvent.__init__(self, zem)
        self.setDaemon(1)
        self.setName("SendEventThread")
        self._evqueue = Queue()

    def sendEvent(self, evt):
        """
        Called from main thread to put an event on to the send queue.
        """
        return self._evqueue.put(evt)


    def run(self):
        """
        Main event loop
        """
        log.info("Starting")
        while not self._evqueue.empty() or self.running:
            try:
                evt = self._evqueue.get(True,1)
                MySqlSendEvent.sendEvent(self, evt)
            except Empty: pass
            except Exception, e:
                log.exception(e)
        log.info("Stopped")


    def stop(self):
        """
        Called from main thread to stop this thread.
        """
        log.info("Stopping...")
        self.running = False
        self.join(3)
