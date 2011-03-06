###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
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

# Filter specific warnings coming from new version of mysql-python
import warnings
warnings.filterwarnings('ignore', r"Field '.+' doesn't have a default value")

from zope.component import getUtility

import Products.ZenUtils.guid as guid
from Event import buildEventFromDict
from ZenEventClasses import Heartbeat, Unknown
from Products.ZenEvents.Exceptions import *
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher

def _execute(cursor, statement):
    """
    Run a MySQL statement and return the results.
    If there's an error, logs it then re-raises the exception.

    @param cursor: an open connection to MySQL
    @type cursor: database connection
    @param statement: MySQL statement
    @type statement: string
    @return: result of the statement
    @rtype: string
    """
    try:
        result = cursor.execute(statement)
        log.debug("%s: --> %d" % (statement, result) )
    except Exception, ex:
        log.info("Invalid statement: %s", statement)
        log.error(str(ex))
        raise ex
    return result

    
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
        Add a heartbeat record to the heartbeat table.

        @param event: event
        @type event: Event class
        """
        evdict = {}
        if hasattr(event, "device"):
            evdict['device'] = event.device
        else:
            log.warn("heartbeat without device skipping")
            return
        if hasattr(event, "timeout"):
            evdict['timeout'] = event.timeout
        else:
            log.warn("heartbeat from %s without timeout skipping", event.device)
            return
        if hasattr(event, "component"):
            evdict['component'] = event.component
        else:
            evdict['component'] = ""
        insert = self.buildInsert(evdict, "heartbeat")
        insert += " on duplicate key update lastTime=Null"
        insert += ", timeout=%s" % evdict['timeout']
        try:
            conn = self.connect()
            try:
                curs = conn.cursor()
                _execute(curs, insert)
            finally: self.close(conn)
        except ProgrammingError, e:
            log.error(insert)
            log.exception(e)
        except OperationalError, e:
            raise ZenBackendFailure(str(e))

    def buildInsert(self, datadict, table):
        """
        Build a insert statement for that looks like this:
        insert into status set field='value', field=1, ...

        @param datadict: event
        @type datadict: dictionary
        @param table: name of the table to insert into
        @type table: string
        @return: MySQL insert command string
        @rtype: string
        """
        insert = "insert into %s set " % table
        fields = []
        for name, value in datadict.items():
            if isinstance(value, basestring):
                fields.append("%s='%s'" % (name, self.escape(value)))
            elif isinstance(value, float):
                fields.append("%s=%.3f" % (name, value))
            else:
                fields.append("%s=%s" % (name, value))
        insert = str(insert) + str(','.join(fields))
        return insert
    
    def escape(self, value):
        """
        Prepare string values for db by escaping special characters.

        @param value: string containing possibly nasty characters
        @type value: string
        @return: escaped string
        @rtype: string
        """
        if not isinstance(value, basestring):
            return value

        import _mysql
        if isinstance(value, unicode):
            return _mysql.escape_string(value.encode('iso-8859-1'))
        return _mysql.escape_string(value)



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
            except OperationalError, e:
                log.warn(e)
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
