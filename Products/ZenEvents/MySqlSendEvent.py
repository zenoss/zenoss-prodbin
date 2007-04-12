import time
import types
import threading
from Queue import Queue, Empty
import logging
log = logging.getLogger("zen.Events")

from _mysql_exceptions import ProgrammingError, OperationalError
from ZEO.Exceptions import ClientDisconnected

import Products.ZenUtils.guid as guid
from Products.ZenUtils.Utils import zdecode as decode
from Event import Event, EventHeartbeat, buildEventFromDict
from ZenEventClasses import Heartbeat, Unknown
from Products.ZenEvents.Exceptions import *

def execute(cursor, statement):
    try:
        result = cursor.execute(statement)
        log.debug("%s: --> %d" % (statement, result) )
    except Exception, ex:
        log.debug(statement)
        log.exception(ex)
        raise ex
    return result

class MySqlSendEventMixin:
    """
    Mix-in class that takes a mysql db connection and builds inserts that
    send the event to the backend.
    """

    def sendEvent(self, event):
        """Send an event to the backend.
        """
        if type(event) == types.DictType:
            event = buildEventFromDict(event)

        if getattr(event, 'eventClass', Unknown) == Heartbeat:
            return self._sendHeartbeat(event)
        
        for field in self.requiredEventFields:
            if not hasattr(event, field):
                raise ZenEventError(
                    "Required event field %s not found" % field)
        
        #FIXME - ungly hack to make sure severity is an int
        event.severity = int(event.severity)
        
        if getattr(self, "getDmdRoot", False):
            try:
                event = self.applyEventContext(event)
            except ClientDisconnected, e:
                log.error(e)
                raise ZenBackendFailure(str(e))
        if not event: return
        
        # check again for heartbeat after context processing
        if getattr(event, 'eventClass', Unknown) == Heartbeat:
            return self._sendHeartbeat(event)
            

        if not hasattr(event, 'dedupid'):
            dedupid = []
            dedupfields = event.getDedupFields(self.defaultEventId)
            if not getattr(event, "eventKey", ""):
                if type(dedupfields) != types.ListType:
                    dedupfields = list(dedupfields)
                dedupfields = dedupfields + ["summary"]
            for field in dedupfields:
                value = getattr(event, field, "")
                dedupid.append('%s' % value)
            dedupid = map(self.escape, dedupid)
            event.dedupid = "|".join(dedupid)

        if getattr(event, "message", False):
            event.summary = event.message[:128]
        if getattr(event, "summary", False):
            event.message = event.summary
            event.summary = event.summary[:128]

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
        return evid

    def doSendEvent(self, event):
        insert = ""
        statusdata, detaildata = self.eventDataMaps(event)
        conn = self.connect()
        try:
            curs = conn.cursor()
            evid = guid.generate()
            event.evid = evid
            if event.severity == 0:
                event._action = "history"
                clearcls = event.clearClasses()
                if clearcls:
                    execute(curs, self.buildClearUpdate(event, clearcls))
                    insert = ('insert into log '
                              '(evid, userName, text) '
                              'select evid, "admin", "auto cleared"'
                              ' from status where clearid = "%s"'  % evid)
                    execute(curs, insert)
            stmt = self.buildStatusInsert(statusdata, event._action, evid)
            rescount = execute(curs, stmt)
            if detaildata and rescount == 1:
                execute(curs, self.buildDetailInsert(evid, detaildata))
            if rescount != 1:
                sql = ('select evid from %s where dedupid="%s"' % (
                        event._action, decode(event.dedupid)))
                execute(curs, sql)
                rs = curs.fetchone()
                if rs:
                    evid = rs[0]
                else:
                    evid = None
            delete = 'DELETE FROM status WHERE clearid IS NOT NULL'
            execute(curs, delete)
        finally: self.close(conn)
        return evid
            

    def applyEventContext(self, evt):
        """Apply event and devices contexts to the event.
        Only valid if this object has zeo connection.
        """
        events = self.getDmdRoot("Events")
        devices = self.getDmdRoot("Devices")
        device = None
        if evt.device:
            device = devices.findDevice(evt.device)
        if not device and hasattr(evt, 'ipAddress'):
            device = devices.findDevice(evt.ipAddress)
            if device:
                evt.device = device.id
            else:
                log.debug("looking up ip %s",evt.ipAddress)
                nets = self.getDmdRoot("Networks")
                ipobj = nets.findIp(evt.ipAddress)
                if ipobj and ipobj.device():
                    device = ipobj.device()
                    evt.device = device.id
                    log.debug("ip %s -> %s", ipobj.id, device.id)
        if device:
            log.debug("Found device=%s", evt.device)
            evt = self.applyDeviceContext(device, evt)
        evtclass = events.lookup(evt, device)
        if evtclass:
            log.debug("EventClassInst=%s", evtclass.id)
            evt = evtclass.applyExtraction(evt)
            evt = evtclass.applyValues(evt)
            evt = evtclass.applyTransform(evt, device)
        if evt._action == "drop": 
            log.debug("dropping event")
            return None
        if getattr(evtclass, "scUserFunction", False):
            log.debug("Found scUserFunction")
            evt = evtclass.scUserFunction(device, evt)
        return evt


    def applyDeviceContext(self, device, evt):
        """
        Apply event attributes from device context.
        """
        evt.prodState = device.productionState
        evt.Location = device.getLocationName()
        evt.DeviceClass  = device.getDeviceClassName()
        evt.DeviceGroups = "|"+"|".join(device.getDeviceGroupNames())
        evt.Systems = "|"+"|".join(device.getSystemNames())
        return evt


    def _sendHeartbeat(self, event):
        """Build insert to add heartbeat record to heartbeat table.
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
            try:
                conn = self.connect()
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
                        self.escape(decode(statusdata.get('summary',''))), 
                        self.countField, self.countField, 
                        self.lastTimeField,statusdata['lastTime'])
        return insert


    def buildDetailInsert(self, evid, detaildict):
        """Build an insert to add detail values from an event to the details
        table.
        """
        insert = "insert into %s (evid, name, value) values " % self.detailTable
        var = [] 
        for field, value in detaildict.items():
            if type(value) in types.StringTypes:
                value = self.escape(value)
            var.append("('%s','%s','%s')" % (evid, field, value)) 
        insert += ",".join(var)        
        return insert


    def buildInsert(self, datadict, table):
        """
        Build a insert statement for that looks like this:
        insert into status set field='value', field=1, ...
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
        """Build an update statement that will clear related events.
        """
        update = "update %s " % self.statusTable
        update += "set clearid = '%s' where " % evt.evid
        w = []
        w.append("%s='%s'" % (self.deviceField, evt.device))
        w.append("%s='%s'" % (self.componentField, evt.component))
        w.append("eventKey='%s'" % evt.eventKey)
        update += " and ".join(w)
        w = []
        for cls in clearcls:
            w.append("%s='%s'" % (self.eventClassField, cls)) 
        if w:
            update += " and (" + " or ".join(w) + ")"
        return update

    
    def eventDataMaps(self, event):
        """Return tuple (statusdata, detaildata) for this event.
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
        """Prepare string values for db by escaping special characters."""
        import _mysql
        if type(value) == type(u''):
            return _mysql.escape_string(value.encode('iso-8859-1'))
        return _mysql.escape_string(value)



class MySqlSendEvent(MySqlSendEventMixin):
    """
    class that can connect to backend must be passed:
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
        
    def stop(self): pass


    def getFieldList(self):
        return self._fieldlist


class MySqlSendEventThread(threading.Thread, MySqlSendEvent):
  
    running = True

    def __init__(self, zem): 
        threading.Thread.__init__(self)
        MySqlSendEvent.__init__(self, zem)
        self.setDaemon(1)
        self.setName("SendEventThread")
        self._evqueue = Queue()

    def sendEvent(self, evt):
        """Called from main thread to put an event on to the send queue.
        """
        return self._evqueue.put(evt)


    def run(self):
        log.info("starting")
        while not self._evqueue.empty() or self.running:
            try:
                evt = self._evqueue.get(True,1)
                MySqlSendEvent.sendEvent(self, evt)
            except Empty: pass
            except OperationalError:
                log.warn(e)
            except Exception, e:
                log.exception(e)
        log.info("stopped")
                
    
    def stop(self):
        """Called from main thread to stop this thread.
        """
        log.info("stopping...")
        self.running = False
        self.join(3)
