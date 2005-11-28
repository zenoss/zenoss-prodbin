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
            insert = self.buildStatusInsert(statusdata)
            log.debug(insert)
            curs = db.cursor()
            rescount = curs.execute(insert)
            if detaildata and rescount == 1:
                curs.execute("select evid from status where dedupid = '%s'"% 
                                    self.escape(event.dedupid))
                evid = curs.fetchone()[0]
                insert = self.buildDetailInsert(evid, detaildata)
                log.debug(insert)
                curs.execute(insert)
            if close: db.close()
            return event
        except ProgrammingError, e:
            print insert
            log.exception(e)
            

    def buildStatusInsert(self, statusdata):
        """
        Build an insert statement for the status table that looks like this:
        insert into status set device='box', count=1, ...
            on duplicate key update count=count+1, lastTime=Null;
        """
        insert = self.buildInsert(statusdata, self.statusTable)
        fields = []
        if not statusdata.has_key(self.firstTimeField):
            fields.append("%s=null" % self.firstTimeField)
        if not statusdata.has_key(self.lastTimeField):
            fields.append("%s=null" % self.lastTimeField)
        fields.append("evid=uuid()")
        insert += ","+",".join(fields)
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
        self.connect()
        while self.running or not self._evqueue.empty():
            try:
                evt = self._evqueue.get(True, 2)        
                self.sendEvent(evt) 
            except Empty: pass
            except OperationalError:
                self.reconnect()
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
                db.close()
                break
            except MySqlError, e:
                slog.warn(e)
                time.sleep(2)
            log.info("reconnected to database: %s", self.database)
