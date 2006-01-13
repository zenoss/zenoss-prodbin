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
    
    def getEventSummary(self, where="", acked=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        select = "select count(*) from %s where " % self.statusTable
        select += where
        if where: select += " and "
        #print select
        sevsum = self.checkCache(select)
        if sevsum: return sevsum
        db = self.connect()
        curs = db.cursor()
        sevsum = []
        for name, value in self.getSeverities():
            sevwhere = " %s = %s" % (self.severityField, value)
            curs.execute(select+sevwhere)
            sevsum.append((self.getEventCssClass(value), curs.fetchone()[0]))
        db.close()
        self.addToCache(select, sevsum)
        self.cleanCache()
        return sevsum


InitializeClass(MySqlEventManager)
