#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""EventManagerBase

$Id: NcoManager.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import logging
import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from Acquisition import aq_base
from OFS.SimpleItem import Item
from OFS.PropertyManager import PropertyManager
from OFS.ObjectManager import ObjectManager
import DateTime

from Products.ZenUtils.ObjectCache import ObjectCache

from interfaces import IEventList, IEventStatus, ISendEvents

from DbAccessBase import DbAccessBase
from Event import eventFromDb


class EventManagerBase(DbAccessBase, ObjectCache, ObjectManager, 
                        PropertyManager, Item):
    """
    Data connector to backend of the event management system.
    """
    #implements(IEventList, IEventStatus, ISendEvents)

    statusTable = "status"
    detailsTable = "details"
    journalTable = "journal"
    LastOccurrence = "LastOccurrence"
    FirstOccurrence = "FirstOccurrence"
    DeviceField = "Node"
    ComponentField = "Component"
    ClassField = "Class"
    SeverityField = "Severity"
    CountField = "Count"
    ProdStateField = "ProdState"
    DeviceGroupField = "DeviceGroups"
    SystemField = "Systems"

    DeviceWhere = "Node = '%s'"
    DeviceResultFields = ("Component", "Class", "Summary", "FirstOccurrence",
                            "LastOccurrence", "Count" )
    ComponentWhere = "Component = '%s'"
    ComponentResultFields = ("Class", "Summary", "FirstOccurrence",
                            "LastOccurrence", "Count" )
    DeviceClassWhere = "DeviceClass = '%s%%%%'"
    LocationWhere = "Location = '%s%%%%'"
    SystemWhere = "Systems like '%%%%|%s%%%%'"
    DeviceGroupWhere = "DeviceGroups like '%%%%|%s%%%%'"

    defaultOrderby = "Severity desc, LastOccurrence desc" 

    defaultResultFields = ("Node", "Component", "Class", "Summary", 
                           "FirstOccurrence", "LastOccurrence", "Count" )

    defaultFields = ('Acknowledged', 'Severity', 'ServerSerial', 'ServerName')

    defaultIdentifier = ('Node', 'Component', 'Class', 'Severity')

    requiredEventFields = ('Node', 'Summary', 'Class', 'Severity')

    refreshConversionsForm = DTMLFile('dtml/refreshNcoProduct', globals())
    
    manage_options = (ObjectManager.manage_options +
                    PropertyManager.manage_options +
                    ({'label':'View', 'action':'viewEvents'}, 
                    {'label':'Refresh', 'action':'refreshConversionsForm'},) +
                    ObjectCache.manage_options +
                    Item.manage_options)

    _properties = (
        {'id':'backend', 'type':'string','mode':'r', },
        {'id':'username', 'type':'string', 'mode':'w'},
        {'id':'password', 'type':'string', 'mode':'w'},
        {'id':'database', 'type':'string', 'mode':'w'},
        {'id':'port', 'type':'int', 'mode':'w'},
        {'id':'defaultWhere', 'type':'text', 'mode':'w'},
        {'id':'defaultOrderby', 'type':'text', 'mode':'w'},
        {'id':'defaultResultFields', 'type':'lines', 'mode':'w'},
        {'id':'statusTable', 'type':'string', 'mode':'w'},
        {'id':'detailsTable', 'type':'string', 'mode':'w'},
        {'id':'journalTable', 'type':'string', 'mode':'w'},
        {'id':'LastOccurrence', 'type':'string', 'mode':'w'},
        {'id':'FirstOccurrence', 'type':'string', 'mode':'w'},
        {'id':'DeviceField', 'type':'string', 'mode':'w'},
        {'id':'ComponentField', 'type':'string', 'mode':'w'},
        {'id':'SeverityField', 'type':'string', 'mode':'w'},
        {'id':'CountField', 'type':'string', 'mode':'w'},
        {'id':'DeviceGroupField', 'type':'string', 'mode':'w'},
        {'id':'SystemField', 'type':'string', 'mode':'w'},
        {'id':'DeviceWhere', 'type':'string', 'mode':'w'},
        {'id':'DeviceResultFields', 'type':'lines', 'mode':'w'},
        {'id':'ComponentWhere', 'type':'string', 'mode':'w'},
        {'id':'ComponentResultFields', 'type':'lines', 'mode':'w'},
        {'id':'DeviceClassWhere', 'type':'string', 'mode':'w'},
        {'id':'LocationWhere', 'type':'string', 'mode':'w'},
        {'id':'SystemWhere', 'type':'string', 'mode':'w'},
        {'id':'DeviceGroupWhere', 'type':'string', 'mode':'w'},
        {'id':'requiredEventFields', 'type':'lines', 'mode':'w'},
        {'id':'defaultIdentifier', 'type':'lines', 'mode':'w'},
        {'id':'defaultFields', 'type':'lines', 'mode':'w'},
        )
    
    security = ClassSecurityInfo()
    

    def __init__(self, id, title='', username='',
                 password='', database='', port=0,
                 defaultWhere='',defaultOrderby='',defaultResultFields=[]):
        self.id = id
        self.title = title
        self.username = username
        self.password = password
        self.database = database
        self.port = port
        self.defaultWhere = defaultWhere

        self.severityCount = 0
        self._schema = {}
        self._conversions = {}  # [Colname] = {Value:Conversion,}
        self._colors = ()
        self._ackedcolors = ()
        ObjectCache.__init__(self)
        self.initCache()

    #==========================================================================
    # Event query functions from IEventQuery
    #==========================================================================

    def getEventListME(self, me, **kwargs):
        where = self.lookupManagedEntityWhere(me)
        resultfields = self.lookupManagedEntityResultFields(me)
        return self.getEventList(resultFields=resultfields,where=where,**kwargs)

        
    def getEventList(self, resultFields=[], where="", orderby="", severity=None,
                    startdate=None, enddate=None, offset=0, rows=0):
        """see IEventList.
        """
        try:
            if not resultFields:
                resultFields = self.defaultResultFields 
            resultFields = list(resultFields)
            resultFields.extend(self.defaultFields)

            select = ["select ", ','.join(resultFields), 
                        "from %s where" % self.statusTable ]
                        
            if not where: 
                where = self.defaultWhere
            where = self._severityWhere(where, severity)
            if startdate:
                startdate, enddate = self._setupDateRange(startdate, enddate)
                where += " and %s >= '%s' and %s <= '%s'" % (
                         self.LastOccurrence, startdate,
                         self.FirstOccurrence, enddate)
            select.append(where)
            if not orderby:
                orderby = self.defaultOrderby
            if orderby:
                select.append("order by")
                select.append(orderby)
            if rows:
                select.append("limit %d, %d" % offset, rows)
            select.append(';')
            select = " ".join(select)
            print select
            retdata = self.checkCache(select)
            if not retdata:
                db = self.connect()
                curs = db.cursor()
                curs.execute(select)
                retdata = self._buildEvents(curs, resultFields)
                db.close()
                self.addToCache(select, retdata)
                self.cleanCache()
            return retdata
        except:
            logging.exception("Failure querying events")
            raise


    def getEventSummaryME(self, me, acked=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        try:
            where = self.lookupManagedEntityWhere(me)
            return self.getEventSummary(where, acked)
        except:
            logging.exception("event summary for %s failed" % me.getDmdKey())
            raise


    def getEventSummary(self, where=None, acked=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        raise NotImplementedError


    def getEventDetail(self, serverserial, servername):
        """Return an EventDetail object for a particular event.
        """
        cachekey = 'ncoeventdetail'+str(serverserial)+servername
        event = self.checkCache(cachekey)
        if event: return event
        db = self.connect()
        fields = self.getFieldList()
        allfields = fields + self.defaultFields
        if ishist:
            nfields=[]
            for field in allfields:
                if self.isDate(field):
                    nfields.append("TO_CHAR(%s, 'YYYY/MM/DD HH24:MI:SS')" 
                                                    % field)
                else:
                    nfields.append(field)
            allfields = nfields
        selectevent = "select " 
        selectevent += ", ".join(allfields)
        selectevent += " from %s where" % self.statusTable
        selectevent += " ServerSerial = " + str(serverserial)
        selectevent += " and ServerName = '" + servername + "'"
        if not ishist: selectevent += ";"
        
        #print selectevent
        curs = db.cursor()
        curs.execute(selectevent)
        evrow = curs.fetchone()
        curs.close()
        if not evrow:
            raise ("NoEventDetailFound", 
                "No Event Detail for Serial %s Server %s" % (
                                    serverserial, servername))
        evrow = map(self.convert, allfields, evrow)
        event = NcoEventDetail(evrow, fields)
        event = event.__of__(self)
        selectdetails = "select Name, Detail from %s where" % (
                                                self.detailsTable)
        selectdetails += " Identifier = '" + event.Identifier + "'"
        if not ishist: selectdetails += ";"
        #print selectdetails
        curs = db.cursor()
        curs.execute(selectdetails)
        detailrows = curs.fetchall()
        details = []
        for name, detail in detailrows:
            ddict = NcoEventData(name, detail)
            details.append(ddict)
        event.details = details
        curs.close()

        selectjournals = "select UID, Chrono, Text1, Text2, Text3, Text4"
        selectjournals += " from %s where" % self.journalTable
        selectjournals += " Serial = " + str(event.Serial)
        if not ishist: selectjournals += ";"
        #print selectjournals
        curs = db.cursor()
        curs.execute(selectjournals)
        jrows = curs.fetchall()
        journals = []
        for row in jrows:
            user = self.convert('OwnerUID', row[0])
            date = self.dateString(row[1])
            textar = map(lambda x: x and x or '', row[2:])
            text = "".join(textar)
            jdict = NcoEventJournal(user,date,text)
            journals.append(jdict)
        event.journals = journals
        curs.close()
        db.close()
        self.addToCache(cachekey, event)
        self.cleanCache()
        return event


    def getStatusME(self, me, statusclass=None, **kwargs):
        """
        """ 
        if me.event_key == "Device":
            return self.getDeviceStatus(me.getId(), statusclass, **kwargs)
        elif me.event_key == "Component":
            return self.getComponentStatus(me.getParentDeviceName(), 
                                      me.getId(), statusclass, **kwargs)
        return self.getOrganizerStatus(me, statusclass=statusclass, **kwargs) 


    def getOrganizerStatus(self,org, statusclass=None, severity=None, where=""):
        """see IEventStatus
        """
        orgfield = self.lookupManagedEntityField(org)
        select = "select %s from %s " % (orgfield, self.statusTable)
        if statusclass: 
            if where: where += " and "
            where += " %s = '%s'" % (self.ClassField, statusclass)
        where = self._severityWhere(where, severity)
        if where: select += "where " + where
        print select
        statusCache = self.checkCache(select)
        if not statusCache:
            db = self.connect()
            curs = db.cursor()
            curs.execute(select)
            statusCache=[]
            orgdict={}
            for row in curs.fetchall():
                orgfield = self.cleanstring(row[0])
                for orgfield in orgfield.split("|"):
                    orgdict.setdefault(orgfield, 0)
                    orgdict[orgfield] += 1
            for key, value in orgdict.items():
                statusCache.append((key, value))
            self.addToCache(select,statusCache)
            db.close()
        countevts = 0
        for key, value  in statusCache:
            if key.startswith(org.getOrganizerName()):
                countevts += value
        return countevts


    def getDeviceStatus(self, device, statclass=None, CountField=None, 
                        severity=None, where=""):
        """see IEventStatus
        """
        if CountField == None: CountField = self.CountField
        select = "select %s, %s from %s where " % (
                  self.DeviceField, self.CountField, self.statusTable)
        if statclass: select += "%s = '%s'" % (self.ClassField, statclass)
        select += self._severityWhere(where, severity)
        print select
        statusCache = self.checkCache(select)
        if not statusCache:
            try:
                db = self.connect()
                curs = db.cursor()
                curs.execute(select)
                statusCache = {}
                for device, count in curs.fetchall():
                    device = self.cleanstring(device)
                    statusCache[device] = count
                self.addToCache(select,statusCache)
                db.close()
            except:
                logging.exception("status failed for device %s", device)
                return -1
        return statusCache.get(device, 0)


    def getComponentStatus(self, device, component, statclass=None, 
                            CountField=None, severity=None, where=""):
        """see IEventStatus
        """
        if CountField == None: CountField = self.CountField
        select = "select %s, %s, %s from %s where "\
                  % (self.DeviceField, self.ComponentField, CountField,
                  self.statusTable)
        if statclass: select += "%s = '%s'" % (self.ClassField, statclass)
        select += self._severityWhere(where, severity)
        statusCache = self.checkCache(select)
        if not statusCache:
            db = self.connect()
            curs = db.cursor()
            curs.execute(select)
            statusCache ={}
            for device, component, count in curs.fetchall():
                device = self.cleanstring(device)
                component = self.cleanstring(component)
                statusCache[device+component] = count
            self.addToCache(select,statusCache)
            db.close()
        return statusCache.get(device+component, 0)


    def lookupManagedEntityWhere(self, managedEntity):
        """Lookup and build where clause for managed entity.
        """
        key = managedEntity.event_key + "Where"
        wheretmpl = getattr(aq_base(self), key, False)
        if not wheretmpl: 
            raise ValueError("no where fround for event_key %s" % 
                            managedEntity.event_key)
        return wheretmpl % managedEntity.getDmdKey()


    def lookupManagedEntityField(self, managedEntity):
        """Lookup database field for managed entity default is event_key.
        """
        key = managedEntity.event_key + "Field"
        return getattr(aq_base(self), key, managedEntity.event_key)


    def lookupManagedEntityResultFields(self, managedEntity):
        """Lookup and result fields for managed entity.
        """
        key = managedEntity.event_key + "ResultFields"
        return getattr(aq_base(self), key, self.defaultResultFields)


    def _severityWhere(self, where, severity):
        if severity != None and where.find(self.SeverityField) == -1:
            if where: where += " and "
            where += " %s >= %s" % (self.SeverityField, severity)
        return where


    def _buildEvents(self, curs, resultFields):
        """check cache and execute query against passed cursor"""
        result = []
        outfields = resultFields[:-len(self.defaultFields)]
        outlen = len(outfields)
        for row in curs.fetchall():
            nrow = []
            for i in range(len(row)):
                if i < outlen:
                    nrow.append(self.convert(outfields[i], row[i]))
                else:
                    nrow.append(self.cleanstring(row[i]))
            evt = eventFromDb(self, nrow, resultFields)
            result.append(evt)
        return result


    def _setupDateRange(self, startdate=DateTime.DateTime(), 
                              enddate=DateTime.DateTime()-1):
        """
        Make a start and end date range that is at least one day long.
        returns a start and end date as a proper database element.
        """
        if type(enddate) == types.StringType:
            enddate = DateTime.DateTime(enddate)
        enddate = enddate.latestTime()
        if type(startdate) == types.StringType:
            startdate = DateTime.DateTime(startdate)
        startdate = startdate.earliestTime()
        startdate = self.dateDB(startdate)
        enddate = self.dateDB(enddate)
        return startdate, enddate
    
    
    #==========================================================================
    # Schema management functions
    #==========================================================================

    security.declareProtected('Send Events', 'sendEvents')
    def sendEvents(self, events):
        """Send a group of events to the backend.
        """
        db = self.connect()
        for event in events:
            self.sendEvent(event, db)
        db.close()


    security.declareProtected('Send Events', 'sendEvent')
    def sendEvent(self, event, db=None):
        """Send an event to the backend.
        """
        for field in self.requiredEventFields:
            if not event.has_key(field):
                raise ZenEventError(
                    "Required event field %s not found" % field)
        
        if not event.has_key('Identifier'):
            evid = []
            for field in self.defaultIdentifier:
                value = event.get(field, "")
                evid.append(str(value))
            event['Identifier'] = "|".join(evid)

        close = False
        if db == None:  
            db = self.connect()
            close = True
        insert = self.buildSendCmd(event)
        print insert
        curs = db.cursor()
        curs.execute(insert)
        if close: db.close()
            


    def buildSendCmd(self, event):
        """Build the insert or update command needed to send event to backend.
        """
        raise NotImplementedError
        
        
    #==========================================================================
    # Schema management functions
    #==========================================================================

    def convert(self, field, value):
        """Perform convertion of value coming from database value if nessesary.
        """
        value = self.cleanstring(value)
        key = field + str(value)
        if self._conversions.has_key(key):
            value = self._conversions[key]
        if self.isDate(field):
            value = self.dateString(value)
        return value


    security.declareProtected("View", "getFieldList")
    def getFieldList(self):
        """Return a list of all fields in the status table of the  backend.
        """
        return self._schema.keys()

    
    security.declareProtected('View','getSeverities')
    def getSeverities(self):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        if not self._conversions: return []
        sevs = [] 
        list = range(self.severityCount)
        list.reverse()
        for i in list:
            sevs.append((self._conversions['Severity'+str(i)], i))
        return sevs

   
    def getStatusCssClass(self, status):
        if status == 0: statname = "clear"
        elif status == 1: statname = "warning"
        elif status == 2: statname = "error"
        elif status >= 3: statname = "critical"
        else: statname = "unknown"
        return self.getCssClass(statname)


    def getCssClass(self, severityname, acked=False):
        """return the css class name to be used for this event.
        """
        acked = acked and "true" or "false"
        return "zenevents_%s_%s" % (severityname.lower(), acked)


    def isDate(self, colName):
        """Check to see if a column is of type date.
        """
        return self._schema.get(colName, False)


    def dateString(self, value):
        """Convert a date from database format to string.
        """
        if isinstance(value, DateTime.DateTime):
            return value.strftime("%Y/%m/%d %H:%M:%S")
        return DateTime.DateTime(value).strftime("%Y/%m/%d %H:%M:%S")


    def dateDB(self, value):
        """Convert a date to its database format.
        """
        if isinstance(value, DateTime.DateTime):
            return value.strftime("%Y/%m/%d %H:%M:%S")
        elif type(value) == types.IntType:
            DateTime.DateTime(value).strftime("%Y/%m/%d %H:%M:%S")
        return value


    def escape(self, value):
        """Prepare string values for db by escaping special characters.
        """
        raise NotImplementedError


    def loadSchema(self, db):
        """Load schema from database. If field is a date set value to true."""
        schema = {}
        sql = "describe %s;" % self.statusTable
        curs = db.cursor()
        curs.execute(sql)
        for row in curs.fetchall():
            col = self.cleanstring(row[0])
            if self.backend == "omnibus":
                type = row[1] in (1, 4, 7, 8) #different date types
            elif self.backend == "mysql":
                type = row[1] in ("datetime", "timestamp")
            schema[col] = type
        if schema: self._schema = schema 
        curs.close()


    security.declareProtected('Manage EventManager','manage_refreshConversions')
    def manage_refreshConversions(self, REQUEST=None):
        """get the conversion information from the omnibus server"""
        conversions = {}
        db = self.connect()
        curs = db.cursor()
        sql = "select KeyField, Conversion, Value from conversions;"
        curs.execute(sql)
        sevcount = 0
        for row in curs.fetchall():
            key = self.cleanstring(row[0])
            conv = self.cleanstring(row[1])
            value = row[2]
            if key.startswith("Severity") and value > -1: 
                sevcount += 1
            conversions[key] = conv
        if conversions: 
            self._conversions = conversions
            self.severityCount = sevcount
        self.loadSchema(db)
        db.close()
        if REQUEST:
            message = "Refreshed Conversions"
            return self.refreshConversionsForm(self, REQUEST, 
                        manage_tabs_message=message)


    security.declareProtected('Manage EventManager','manage_editCache')
    def manage_editCache(self, timeout=20, clearthresh=20, REQUEST=None):
        """Reset cache values"""
        self.timeout = int(timeout)
        self.clearthresh = int(clearthresh)
        if REQUEST:
            message = "Cache parameters set"
            return self.editCache(self, REQUEST, manage_tabs_message=message)
   

    security.declareProtected('Manage EventManager','manage_clearCache')
    def manage_clearCache(self, REQUEST=None):
        """Reset cache values"""
        self.cleanCache(force=1)
        if REQUEST:
            message = "Cache cleared"
            return self.editCache(self, REQUEST, manage_tabs_message=message)
  
    
    #==========================================================================
    # Utility functions
    #==========================================================================

    def installIntoPortal(self):
        """Install skins into portal.
        """
        from Products.CMFCore.utils import getToolByName
        from Products.CMFCore.DirectoryView import addDirectoryViews
        from cStringIO import StringIO
        import string

        out = StringIO()
        skinstool = getToolByName(self, 'portal_skins') 
        if 'zenevents' not in skinstool.objectIds():
            addDirectoryViews(skinstool, 'skins', globals())
            out.write("Added 'zenevents' directory view to portal_skins\n")
        skins = skinstool.getSkinSelections()
        for skin in skins:
            path = skinstool.getSkinPath(skin)
            path = map(string.strip, string.split(path,','))
            if 'zenevents' not in path:
                try: path.insert(path.index('zenmodel'), 'zenevents')
                except ValueError:
                    path.append('zenevents')
                path = string.join(path, ', ')
                skinstool.addSkinSelection(skin, path)
                out.write("Added 'zenevents' to %s skin\n" % skin)
            else:
                out.write(
                    "Skipping %s skin, 'zenevents' is already set up\n" % skin) 
        return out.getvalue()

