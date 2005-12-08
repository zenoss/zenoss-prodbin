import time
import types
import threading
from Queue import Queue, Empty
import logging
log = logging.getLogger("SendEvent")

from _mysql_exceptions import ProgrammingError, OperationalError

from DbAccessBase import DbAccessBase
from Event import Event
from Exceptions import *

class MySqlSendEventMixin:
    """
    Mix-in class that takes a mysql db connection and builds inserts that
    send the event to the backend.
    """

    def sendEvent(self, event, db=None):
        """Send an event to the backend.
        """
        if type(event) == types.DictType:
            nevt = Event()
            nevt.updateFromDict(event)
            event = nevt
        #FIXME - ungly hack to make sure severity is an int
        event.severity = int(event.severity)

        for field in self.requiredEventFields:
            if not hasattr(event, field):
                raise ZenEventError(
                    "Required event field %s not found" % field)
        
        if not hasattr(event, 'dedupid'):
            evid = []
            dedupfields = getattr(event, "dedupfields", self.defaultIdentifier)
            for field in dedupfields:
                value = getattr(event, field, "")
                evid.append(str(value))
            event.dedupid = "|".join(evid)

        insert = ""
        try:
            close = False
            if db == None:  
                db = self.connect()
                close = True
            statusdata, detaildata = self.eventDataMaps(event)
            curs = db.cursor()
            if event.severity == 0:
                event._action = "history"
                clearcls = event.clearClasses()
                if clearcls:
                    delete = self.buildClearDelete(event, clearcls)
                    log.debug(delete)
                    curs.execute(delete)
            insert = self.buildStatusInsert(statusdata, event._action)
            log.debug(insert)
            rescount = curs.execute(insert)
            if detaildata and rescount == 1:
                curs.execute("select evid from %s where dedupid = '%s "
                             "order by lastTime desc limit 1'"% (
                             event._action, self.escape(event.dedupid)))
                evid = curs.fetchone()[0]
                insert = self.buildDetailInsert(evid, detaildata)
                log.debug(insert)
                curs.execute(insert)
            if close: db.close()
            return event
        except ProgrammingError, e:
            print insert
            log.exception(e)
            

    def buildStatusInsert(self, statusdata, table):
        """
        Build an insert statement for the status table that looks like this:
        insert into status set device='box', count=1, ...
            on duplicate key update count=count+1, lastTime=Null;
        """
        insert = self.buildInsert(statusdata, table)
        fields = []
        if not statusdata.has_key(self.firstTimeField):
            fields.append("%s=null" % self.firstTimeField)
        if not statusdata.has_key(self.lastTimeField):
            fields.append("%s=null" % self.lastTimeField)
        if table == "history":
            fields.append("deletedTime=null")
        fields.append("evid=uuid()")
        insert += ","+",".join(fields)
        if table == self.statusTable:
            insert += " on duplicate key update "
            insert += "%s=%s+1,%s=null" % (self.countField, self.countField, 
                                            self.lastTimeField)
        return insert


    def buildDetailInsert(self, evid, detaildict):
        insert = "insert into %s (evid, name, value) values " % self.detailTable
        var = [] 
        for field, value in detaildict.items():
            var.append("('%s','%s','%s')" % (evid, field, self.escape(value))) 
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
            if type(value) == types.StringType:
                fields.append("%s='%s'" % (name, self.escape(value)))
            else:
                fields.append("%s=%s" % (name, value))
        insert += ",".join(fields)
        return insert


    def buildClearDelete(self, evt, clearcls):
        """Build a delete statement that will clear related events.
        """
        delete = "delete from %s where " % self.statusTable
        w = []
        w.append("%s='%s'" % (self.deviceField, evt.device))
        w.append("%s='%s'" % (self.componentField, evt.component))
        w.append("eventKey='%s'" % evt.eventKey)
        delete += " and ".join(w)
        w = []
        for cls in clearcls:
            w.append("%s='%s'" % (self.eventClassField, cls)) 
        if w:
            delete += " and " + " or ".join(w)
        return delete

    
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
        return _mysql.escape_string(value)



class MySqlSendEvent(DbAccessBase, MySqlSendEventMixin):
    """
    class that can connect to backend must be passed:
        username - backend username to use
        password - backend password
        database - hostname of box (in mysql case) or database name
        port - port (for mysql)
    """
    backend = "mysql"

    copyattrs = (
        "username",
        "password",
        "database",
        "port",
        "requiredEventFields",
        "defaultIdentifier",
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


    def getqueue(self):
        return self._evqueue


    def run(self):
        log.info("starting")
        db = self.connect()
        while not self._evqueue.empty() or self.running:
            try:
                evt = self._evqueue.get()        
                self.sendEvent(evt, db) 
            except Empty: time.sleep(1)
            except OperationalError:
                db =self.reconnect()
            except Exception, e: 
                log.exception(e) 
        db.close()
        log.info("stopped")
                
    
    def stop(self):
        log.info("stopping")
        self.running = False


    def reconnect(self):
        while self.running:
            try:
                db = self.connect()
                curs = db.cursor()
                curs.execute("select count(*) from status")
                curs.close()
                return db
            except MySqlError, e:
                slog.warn(e)
                time.sleep(2)
            log.info("reconnected to database: %s", self.database)
