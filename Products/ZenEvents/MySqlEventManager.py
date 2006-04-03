import types
import logging
log = logging.getLogger("zen.Events")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo

from EventManagerBase import EventManagerBase
from MySqlSendEvent import MySqlSendEventMixin
from Exceptions import *

def manage_addMySqlEventManager(context, id=None, evtuser="root", evtpass="",
                                history=False, REQUEST=None):
    '''make an MySqlEventManager'''
    if not id: 
        id = "ZenEventManager"
        if history: id = "ZenEventHistory"
    evtmgr = MySqlEventManager(id,username=evtuser,password=evtpass) 
    context._setObject(id, evtmgr)
    evtmgr = context._getOb(id)
    try:
        evtmgr.manage_refreshConversions()
    except:
        log.warn("Failed to refresh conversions, db connection failed.")
    if history: 
        evtmgr.statusTable = "history"
    evtmgr.installIntoPortal()
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


addMySqlEventManager = DTMLFile('dtml/addMySqlEventManager',globals())


class MySqlEventManager(MySqlSendEventMixin, EventManagerBase):

    portal_type = meta_type = 'MySqlEventManager'
   
    backend = "mysql"

    security = ClassSecurityInfo()
    
    def getEventSummary(self, where="", severity=1, state=1):
        """
        Return a list of tuples with the CSS class, acknowledged count, count

        [['zenevents_5', 0, 3], ...]

        select severity, count(*), group_concat(eventState), 
            from status where device="win2k.confmon.loc" 
            and eventState < 2 group by severity desc;
        """ 
        select = "select severity, count(*), group_concat(eventState) "
        select += "from %s where " % self.statusTable
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        select += " group by severity desc"
        #print select
        sevsum = self.checkCache(select)
        if sevsum: return sevsum
        db = self.connect()
        curs = db.cursor()
        curs.execute(select)
        sumdata = {}
        ownerids = ""
        for row in curs.fetchall():
            sev, count, acks = row[:3]
            if type(acks) in types.StringTypes:
                acks = acks.split(",")
            ackcount = sum([int(n) for n in acks if n.strip()])
            sumdata[sev] = (ackcount, count)
        sevsum = []
        for name, value in self.getSeverities():
            if value < severity: continue
            css = self.getEventCssClass(value)
            ackcount, count = sumdata.get(value, [0,0])
            sevsum.append([css, ackcount, int(count)])
        db.close()
        self.addToCache(select, sevsum)
        self.cleanCache()
        return sevsum


InitializeClass(MySqlEventManager)

