import types
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from EventManagerBase import EventManagerBase

def manage_addMySqlEventManager(context, id=None, REQUEST=None):
    '''make an MySqlEventManager'''
    if not id: id = "ZenEventManager"
    ncp = MySqlEventManager(id) 
    context._setObject(id, ncp)
    ncp = context._getOb(id)
    ncp.installIntoPortal()
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
        select += "%s = %%s" % self.SeverityField
        print select
        sevsum = self.checkCache(select)
        if sevsum: return sevsum
        db = self.connect()
        curs = db.cursor()
        sevsum = []
        for name, value in self.getSeverities():
            curs.execute(select, (value,))
            sevsum.append((self.getCssClass(name), curs.fetchone()[0]))
        db.close()
        self.addToCache(select, sevsum)
        self.cleanCache()
        return sevsum
            
        

    def buildSendCmd(self, event):
        """
        insert into status (Node, Count) values ('box', 0)
            on duplicate key update Count=Count+1, LastOccurrence=Null;
        """
        insert = "insert into %s (" % self.statusTable
        insert += ",".join(event.keys())
        insert += ',FirstOccurrence, LastOccurrence, Count, EventUuid'
        insert += ") values ("
        inar = []
        for value in event.values():
            if type(value) == types.IntType or type(value) == types.LongType:
                inar.append(str(value))
            else:
                inar.append("'"+self.escape(value)+"'")
        insert += ",".join(inar)
        insert += ",NULL,NULL,1,UUID()"
        insert += ")"
        insert += " on duplicate key update Count=Count+1, LastOccurrence=Null;"
        return insert


    def escape(self, value):
        """Prepare string values for db by escaping special characters."""
        import _mysql
        return _mysql.escape_string(value)


InitializeClass(MySqlEventManager)
