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

import types
import threading
from Queue import Queue, Empty
import logging
log = logging.getLogger("zen.Events")

# Filter specific warnings coming from new version of mysql-python
import warnings
warnings.filterwarnings('ignore', r"Field '.+' doesn't have a default value")

from zope.component import getUtility
from ZEO.Exceptions import ClientDisconnected

import Products.ZenUtils.guid as guid
from Products.ZenUtils.Utils import zdecode as decode
from Event import buildEventFromDict
from ZenEventClasses import Heartbeat, Unknown
from Products.ZenEvents.Exceptions import *
from Products.ZenUtils.Utils import zdecode
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


class EventTransformer(object):
    def __init__(self, dbref, evt, evtFields, reqdEvtFields, dedupEvtFields):
        self.dmd = dbref.getDmd()
        self.eventFields = evtFields
        self.requiredEventFields = reqdEvtFields
        self.dedupEventFields = dedupEvtFields
        self.event = evt
        self.deviceObj = None

    def prepEvent(self):
        event = self.event
        if not all(getattr(event,field,None) is not None for field in self.requiredEventFields):
            for field in self.requiredEventFields:
                if getattr(event, field, None) is None:
                    log.error("Required event field %s not found" \
                              " -- ignoring event", field)
                    statusdata, detaildata = self._eventDataMaps()
                    log.error("Event info: %s", statusdata)
                    if detaildata:
                        log.error("Detail data: %s", detaildata)
                    self.evtdetails = detaildata
                    return False
        
        #FIXME - ungly hack to make sure severity is an int
        try:
            event.severity = int(event.severity)
        except:
            event.severity = 1  # Info

        # Check for nasty haxor tricks
        known_actions = [ 'history', 'drop', 'status', 'heartbeat',
                          'alert_state', 'log', 'detail',
                        ]
        if getattr( event, '_action', None ) not in known_actions:
            event._action = 'status'

        # If either message or summary is empty then try to copy from the other.
        # Make sure summary is truncated to 128
        if not getattr(event, 'message', False):
            event.message = getattr(event, 'summary', '')
        event.summary = (getattr(event, 'summary', '') or event.message)[:128]

        if getattr(self, "_getDmdRoot", False):
            try:
                keepevent = self._applyEventContext(event)
            except ClientDisconnected, e:
                log.error(e)
                raise ZenBackendFailure(str(e))
            if not keepevent:
                log.debug("Unable to obtain event -- ignoring.(%s)", event)
                return False

        return True
    
    def transformEvent(self):
        event = self.event
        statusdata, detaildata = self._eventDataMaps()
        log.debug("Event info: %s", statusdata)
        if detaildata:
            log.debug("Detail data: %s", detaildata)

        if not getattr(event, 'dedupid', ''):
            dedupfields = self.dedupEventFields
            if not getattr(event, "eventKey", ""):
                if isinstance(dedupfields, basestring):
                    dedupfields = [dedupfields]
                if not isinstance(dedupfields, list):
                    dedupfields = list(dedupfields)
                if "summary" not in dedupfields:
                    dedupfields.append("summary")

            if dedupfields:
                dedupidlist = [str(getattr(event, field, "")) for field in dedupfields]
            else:
                dedupidlist = []
            event.dedupid = "|".join(dedupidlist)
            log.debug("Created dedupid of %s", event.dedupid)

        # fix string encoding on selected fields that are likely to contain 
        # characters outside the ASCII 7-bit range
        if self.deviceObj is not None:
            devicecontext = self.deviceObj
        else:
            devicecontext = self.dmd.Devices

        for attrname in "summary message device component service".split():
            if getattr(event, attrname, False):
                setattr(event, attrname, zdecode(devicecontext, getattr(event, attrname)))

        return True

    def _eventDataMaps(self):
        """
        Return tuple (statusdata, detaildata) for this event.

        @param event: event
        @type event: Event class
        @return: (statusdata, detaildata)
        @rtype: tuple of dictionaries
        """
        event = self.event
        statusfields = self.eventFields
        statusdata = {}
        detaildata = {}
        for name, value in event.__dict__.items():
            if name[0] == "_": continue
            if name in statusfields:
                statusdata[name] = value
            else:
                detaildata[name] = value
        return statusdata, detaildata

    def _getDmdRoot(self, name):
        return self.dmd._getOb(name)

    def _findByIp(self, ipaddress, networks):
        """
        Find and ip by looking up it up in the Networks catalog.

        @param ipaddress: IP address
        @type ipaddress: string
        @param networks: DMD network object
        @type networks: DMD object
        @return: device object
        @rtype: device object
        """
        log.debug("Looking up IP %s" % ipaddress)
        ipobj = networks.findIp(ipaddress)
        if ipobj and ipobj.device():
            device = ipobj.device()
            log.debug("IP %s -> %s", ipobj.id, device.id)
            return device

    def _applyEventContext(self, evt):
        """
        Apply event and devices contexts to the event.
        Only valid if this object has zeo connection.

        @param evt: event
        @type evt: Event class
        @return: flag indicating whether event should be kept/stored
        @rtype: boolean
        """
        events = self._getDmdRoot("Events")
        devices = self._getDmdRoot("Devices")
        networks = self._getDmdRoot('Networks')

        # if the event has a monitor field use the PerformanceConf
        # findDevice so that the find is scoped to the monitor (collector)
        if getattr(evt, 'monitor', False):
            monitorObj = self._getDmdRoot('Monitors'
                            ).Performance._getOb(evt.monitor, None)
            if monitorObj:
                devices = monitorObj

        # Look for the device by name, then IP 'globally'
        # and then from the /Network class
        device = None
        if getattr(evt, 'device', None):
            device = devices.findDevice(evt.device)
        if not device and getattr(evt, 'ipAddress', None):
            device = devices.findDevice(evt.ipAddress)
        if not device and getattr(evt, 'device', None):
            device = self._findByIp(evt.device, networks)
        if not device and getattr(evt, 'ipAddress', None):
            device = self._findByIp(evt.ipAddress, networks)

        if device:
            self.deviceObj = device
            evt.device = device.id
            log.debug("Found device %s and adding device-specific"
                      " data", evt.device)
            
            # apply device context info
            # evt = self.applyDeviceContext(device, evt)
            if not getattr(evt, 'ipAddress', None):
                evt.ipAddress = device.manageIp
            evt.prodState = device.productionState
            evt.Location = device.getLocationName()
            evt.DeviceClass  = device.getDeviceClassName()
            evt.DeviceGroups = "|"+"|".join(device.getDeviceGroupNames())
            evt.Systems = "|"+"|".join(device.getSystemNames())
            evt.DevicePriority = device.getPriority()

        evtclass = events.lookup(evt, device)
        if evtclass:
            evt = evtclass.applyExtraction(evt)
            evt = evtclass.applyValues(evt)
            evt = evtclass.applyTransform(evt, device)

        if evt._action == "drop":
            log.debug("Dropping event")
            return False

        return True

    
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
        _, detaildata = self.eventDataMaps(event)
        self._publishEvent(event, detaildata)
        return event.evid

    def _publishEvent(self, event, detaildata):
        """
        Sends this event to the event fan out queue
        """
        publisher = getUtility(IEventPublisher)
        event.detaildata = detaildata
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

    def eventDataMaps(self, event):
        """
        Return tuple (statusdata, detaildata) for this event.

        @param event: event
        @type event: Event class
        @return: (statusdata, detaildata)
        @rtype: tuple of dictionaries
        """
        statusfields = self.getFieldList()
        statusdata = {}
        detaildata = {}
        for name, value in event.__dict__.items():
            if name.startswith("_") or name == "dedupfields": continue
            if name in statusfields:
                statusdata[name] = value
            else:
                detaildata[name] = value
        return statusdata, detaildata
    
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
