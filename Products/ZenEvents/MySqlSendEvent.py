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

from _mysql_exceptions import ProgrammingError, OperationalError
from ZEO.Exceptions import ClientDisconnected

import Products.ZenUtils.guid as guid
from Products.ZenUtils.Utils import zdecode as decode
from Event import buildEventFromDict
from ZenEventClasses import Heartbeat, Unknown
from Products.ZenEvents.Exceptions import *

def execute(cursor, statement):
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
        log.debug('%s%s%s' % ('=' * 15, '  incoming event  ', '=' * 15))
        if type(event) == types.DictType:
            event = buildEventFromDict(event)

        if getattr(event, 'eventClass', Unknown) == Heartbeat:
            log.debug("Got a %s %s heartbeat event (timeout %s sec).",
                      getattr(event, 'device', 'Unknown'),
                      getattr(event, 'component', 'Unknown'),
                      getattr(event, 'timeout', 'Unknown'))
            return self._sendHeartbeat(event)
        
        for field in self.requiredEventFields:
            if not hasattr(event, field):
                raise ZenEventError(
                    "Required event field %s not found" % field)

        #FIXME - ungly hack to make sure severity is an int
        try:
            event.severity = int(event.severity)
        except:
            event.severity = 1  # Info

        # Check for nasty haxor tricks
        known_actions = [ 'history', 'drop', 'status', 'heartbeat',
                          'alert_state', 'log', 'detail',
                        ]
        if hasattr( event, '_action' ) and event._action not in known_actions:
            event._action = 'status'
        
        # If either message or summary is empty then try to copy from the other.
        # Make sure summary is truncated to 128
        if not getattr(event, 'message', False):
            event.message = getattr(event, 'summary', '')
        event.summary = (getattr(event, 'summary', '') or event.message)[:128]
        
        statusdata, detaildata = self.eventDataMaps(event)
        log.debug("Event info: %s", statusdata)
        if detaildata:
            log.debug("Detail data: %s", detaildata)

        if getattr(self, "getDmdRoot", False):
            try:
                event = self.applyEventContext(event)
            except ClientDisconnected, e:
                log.error(e)
                raise ZenBackendFailure(str(e))
        if not event:
            log.debug("Unable to obtain event -- ignoring.(%s)", event)
            return
        
        # check again for heartbeat after context processing
        if getattr(event, 'eventClass', Unknown) == Heartbeat:
            log.debug("Transform created a heartbeat event.")
            return self._sendHeartbeat(event)
            

        if not hasattr(event, 'dedupid'):
            dedupfields = event.getDedupFields(self.defaultEventId)
            if not getattr(event, "eventKey", ""):
                if type(dedupfields) != types.ListType:
                    dedupfields = list(dedupfields)
                dedupfields = dedupfields + ["summary"]

            dedupid = []
            for field in dedupfields:
                value = getattr(event, field, "")
                dedupid.append('%s' % value)
            dedupid = map(self.escape, dedupid)
            event.dedupid = "|".join(dedupid)
            log.debug("Created deupid of %s", event.dedupid)

        # WTH is 'cleanup' supposed to do? Never gets used
        cleanup = lambda : None
        evid = None
        try:
            try:
                evid = self.doSendEvent(event)
            except ProgrammingError, e:
                log.exception(e)
            except OperationalError, e:
                log.exception(e)
                raise ZenBackendFailure(str(e))
        finally:
            cleanup()

        if evid:
            log.debug("New event id = %s", evid)
        else:
            log.debug("Duplicate event, updated database.")
        return evid


    def doSendEvent(self, event):
        """
        Actually write the sanitized event into the database

        @param event: event   
        @type event: Event class
        @return: event id or None
        @rtype: string
        """
        insert = ""
        statusdata, detaildata = self.eventDataMaps(event)
        if int(event.severity) == 0:
            log.debug("Clear event found with event data %s",
                  statusdata)
        else:
            log.debug("Performing action '%s' on event %s",
                  event._action, statusdata)
        if detaildata:
            log.debug("Detail data: %s", detaildata)

        conn = self.connect()
        try:
            curs = conn.cursor()
            evid = guid.generate()
            event.evid = evid
            rows = 0
            if int(event.severity) == 0:
                event._action = "history"
                clearcls = event.clearClasses()
                if not clearcls:
                    log.debug("No clear classes in event -- no action taken.")
                else:
                    rows = execute(curs, self.buildClearUpdate(event, clearcls))
                    log.debug("%d events matched clear criteria", rows)
                    if not rows:
                        return None
                    insert = ('insert into log '
                              '(evid, userName, text) '
                              'select evid, "admin", "auto cleared"'
                              ' from status where clearid = "%s"'  % evid)
                    execute(curs, insert)
                    delete = 'DELETE FROM status WHERE clearid IS NOT NULL'
                    execute(curs, delete)
            stmt = self.buildStatusInsert(statusdata, event._action, evid)
            rescount = execute(curs, stmt)
            if detaildata and rescount == 1:
                execute(curs, self.buildDetailInsert(evid, detaildata))
            if rescount != 1:
                sql = ('select evid from %s where dedupid="%s"' % (
                        event._action, decode(self.dmd.Devices, event.dedupid)))
                log.debug("%d events returned from insert -- selecting first match from %s.",
                          rescount, sql)
                execute(curs, sql)
                rs = curs.fetchone()
                if rs:
                    evid = rs[0]
                else:
                    log.debug("No matches found")
                    evid = None
        finally: self.close(conn)
        return evid
           

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


    def getNetworkRoot(self, evt):
        """
        Return the network root and event

        @param evt: event
        @type evt: Event class
        @return: DMD object and the event
        @rtype: DMD object, evt
        """
        return self.getDmdRoot('Networks'), evt


    def applyEventContext(self, evt):
        """
        Apply event and devices contexts to the event.
        Only valid if this object has zeo connection.

        @param evt: event
        @type evt: Event class
        @return: updated event
        @rtype: Event class
        """
        events = self.getDmdRoot("Events")
        devices = self.getDmdRoot("Devices")
        networks, evt = self.getNetworkRoot(evt)

        # if the event has a monitor field use the PerformanceConf 
        # findDevice so that the find is scoped to the monitor (collector)
        if getattr(evt, 'monitor', False):
            monitorObj = self.getDmdRoot('Monitors'
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
            evt.device = device.id
            log.debug("Found device %s and adding device-specific"
                      " data", evt.device)
            evt = self.applyDeviceContext(device, evt)

        evtclass = events.lookup(evt, device)
        if evtclass:
            evt = evtclass.applyExtraction(evt)
            evt = evtclass.applyValues(evt)
            evt = evtclass.applyTransform(evt, device)

        if evt._action == "drop": 
            log.debug("Dropping event")
            return None

        return evt


    def applyDeviceContext(self, device, evt):
        """
        Apply event attributes from device context.

        @param device: device from DMD
        @type device: device object
        @param evt: event
        @type evt: Event class
        @return: updated event
        @rtype: Event class
        """
        if not hasattr(evt, 'ipAddress'): evt.ipAddress = device.manageIp
        evt.prodState = device.productionState
        evt.Location = device.getLocationName()
        evt.DeviceClass  = device.getDeviceClassName()
        evt.DeviceGroups = "|"+"|".join(device.getDeviceGroupNames())
        evt.Systems = "|"+"|".join(device.getSystemNames())
        evt.DevicePriority = device.getPriority()
        return evt


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
                execute(curs, insert)
            finally: self.close(conn)
        except ProgrammingError, e:
            log.error(insert)
            log.exception(e)
        except OperationalError, e:
            raise ZenBackendFailure(str(e))


    def buildStatusInsert(self, statusdata, table, evid):
        """
        Build an insert statement for the status table that looks like this:
        insert into status set device='box', count=1, ...
            on duplicate key update count=count+1, lastTime=23424.34;

        @param statusdata: event
        @type statusdata: dictionary
        @param table: name of the table to insert into
        @type table: string
        @param evid: event id
        @type evid: string
        @return: MySQL insert command string
        @rtype: string
        """
        insert = self.buildInsert(statusdata, table)
        fields = []
        if table == "history":
            fields.append("deletedTime=null")
        fields.append("evid='%s'" % evid)
        insert += ","+",".join(fields)
        if table == self.statusTable:
            insert += " on duplicate key update "
            if statusdata.has_key('prodState'):
                insert += "prodState=%d," % statusdata['prodState']
            insert += "summary='%s',%s=%s+1,%s=%.3f" % (
                        self.escape(decode(self.dmd.Devices, statusdata.get('summary',''))), 
                        self.countField, self.countField, 
                        self.lastTimeField,statusdata['lastTime'])
        return insert


    def buildDetailInsert(self, evid, detaildict):
        """
        Build an insert to add detail values from an event to the details
        table.

        @param evid: event id
        @type evid: string
        @param detaildict: event
        @type detaildict: dictionary
        @return: MySQL insert command string
        @rtype: string
        """
        insert = "insert into %s (evid, name, value) values " % self.detailTable
        var = [] 
        for field, value in detaildict.items():
            if type(value) in types.StringTypes:
                value = self.escape(decode(self.dmd.Devices, value))
            var.append("('%s','%s','%s')" % (evid, field, value)) 
        insert += ",".join(var)        
        return insert


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
            if type(value) in types.StringTypes:
                fields.append("%s='%s'" % (name, self.escape(value)))
            elif type(value) == types.FloatType:
                fields.append("%s=%.3f" % (name, value))
            else:
                fields.append("%s=%s" % (name, value))
        insert = str(insert) + str(','.join(fields))
        return insert


    def buildClearUpdate(self, evt, clearcls):
        """
        Build an update statement that will clear related events.

        @param evt: event
        @type evt: Event class
        @param clearcls: other fields to use to define 'related events'
        @type clearcls: list of strings
        @return: MySQL update command string
        @rtype: string
        """
        update = "update %s " % self.statusTable
        update += "set clearid = '%s' where " % evt.evid
        w = []
        w.append("%s='%s'" % (self.deviceField, self.escape(evt.device)))
        w.append("%s='%s'" % (self.componentField,
            self.escape(evt.component)[:255]))
        w.append("eventKey='%s'" % self.escape(evt.eventKey)[:128])
        update += " and ".join(w)

        w = []
        for cls in clearcls:
            w.append("%s='%s'" % (self.eventClassField, self.escape(cls))) 
        if w:
            update += " and (" + " or ".join(w) + ")"
        log.debug("Clear command: %s", update)
        return update

    
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
        if type(value) not in types.StringTypes:
            return value
            
        import _mysql
        if type(value) == type(u''):
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
