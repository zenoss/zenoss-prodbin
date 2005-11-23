import types
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from EventManagerBase import EventManagerBase
from Exceptions import *

def manage_addMySqlEventManager(context, id=None, history=False, REQUEST=None):
    '''make an MySqlEventManager'''
    if not id: 
        id = "ZenEventManager"
        if history: id = "ZenEventHistory"
    evtmgr = MySqlEventManager(id) 
    context._setObject(id, evtmgr)
    evtmgr = context._getOb(id)
    if history: 
        evtmgr.status = "history"
        evtmgr.defaultOrderby="%s asc" % evtmgr.LastOccurrenceField
    evtmgr.installIntoPortal()
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')



class MySqlEventManager(EventManagerBase):

    portal_type = meta_type = 'MySqlEventManager'
   
    backend = "mysql"

    security = ClassSecurityInfo()
    
    def getEventSummary(self, where="", acked=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        select = "select count(*) from %s where " % self.statusTable
        select += where
        if where: select += " and "
        select += "%s = %%s" % self.severityField
        #print select
        sevsum = self.checkCache(select)
        if sevsum: return sevsum
        db = self.connect()
        curs = db.cursor()
        sevsum = []
        for name, value in self.getSeverities():
            curs.execute(select, (value,))
            sevsum.append((self.getEventCssClass(value), curs.fetchone()[0]))
        db.close()
        self.addToCache(select, sevsum)
        self.cleanCache()
        return sevsum


    security.declareProtected('Send Events', 'sendEvent')
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
            for field in self.defaultIdentifier:
                value = getattr(event, field, "")
                evid.append(str(value))
            event.dedupid = "|".join(evid)

        close = False
        if db == None:  
            db = self.connect()
            close = True
        
        statusdata, detaildata = self.eventDataMaps(event)
        insert = self.buildStatusInsert(statusdata)
        #print insert
        curs = db.cursor()
        rescount = curs.execute(insert)
        if detaildata and rescount == 1:
            curs.execute("select evid from status where dedupid = '%s'"% 
                                event.dedupid)
            evid = curs.fetchone()[0]
            insert = self.buildDetailInsert(evid, detaildata)
            #print insert
            curs.execute(insert)
        if close: db.close()
        return event
            

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
            if type(value) == types.StringType:
                fields.append("%s='%s'" % (name, self.escape(value)))
            else:
                fields.append("%s=%s" % (name, value))
        insert += ",".join(fields)
        return insert


    def escape(self, value):
        """Prepare string values for db by escaping special characters."""
        import _mysql
        return _mysql.escape_string(value)


InitializeClass(MySqlEventManager)
