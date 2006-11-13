#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################

"""EventManagerBase

$Id: NcoManager.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import time
import types
import random
random.seed()
import logging
log = logging.getLogger("zen.Events")

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Globals import InitializeClass
from Globals import DTMLFile
from Acquisition import aq_base
from OFS.SimpleItem import Item
from OFS.PropertyManager import PropertyManager
from OFS.ObjectManager import ObjectManager
import DateTime
from AccessControl import Permissions as permissions

from Products.ZenUtils.ObjectCache import ObjectCache
from Products.ZenModel.Organizer import Organizer

from interfaces import IEventList, IEventStatus, ISendEvents

from DbAccessBase import DbAccessBase
from ZEvent import ZEvent
from EventDetail import EventDetail
from Exceptions import *

from Products.ZenModel.ZenModelItem import ZenModelItem
from Products.ZenUtils import Time

from ZenEventClasses import Unknown

import time

class EventManagerBase(ZenModelItem, DbAccessBase, ObjectCache, ObjectManager, 
                        PropertyManager, Item):
    """
    Data connector to backend of the event management system.
    """
    #implements(IEventList, IEventStatus, ISendEvents)

    #FQDNID = hash(socket.getfqdn())

    eventStateConversions = (
                ('New',         0),
                ('Acknowledged',1),
                ('Suppressed',  2),
                #('Bogus',       3),
                )

    severities = ['Clear', 'Debug', 'Info', 'Warning', 'Error', 'Critical']

    severityConversions = [(s, i) for i, s in enumerate(severities)]
    severityConversions.reverse()
    severityConversions = tuple(severityConversions)
    
    statusTable = "status"
    detailTable = "detail"
    logTable = "log"
    lastTimeField = "lastTime"
    firstTimeField = "firstTime"
    deviceField = "device"
    componentField = "component"
    eventClassField = "eventClass"
    severityField = "severity"
    stateField = "eventState"
    countField = "count"
    prodStateField = "prodState"
    DeviceGroupField = "DeviceGroups"
    SystemField = "Systems"

    DeviceWhere = "\"device = '%s'\" % me.getDmdKey()"
    DeviceResultFields = ("component", "eventClass", "summary", "firstTime",
                            "lastTime", "count" )
    ComponentWhere = "component = '%s'"
    ComponentResultFields = ("eventClass", "summary", "firstTime",
                            "lastTime", "count" )
    IpAddressWhere = "\"ipAddress='%s'\" % (me.getId())" 
    EventClassWhere = "\"eventClass like '%s%%'\" % me.getDmdKey()"
    EventClassInstWhere = """\"eventClass = '%s' and eventClassKey = '%s'\" % (\
                                me.getEventClass(), me.eventClassKey)""" 
    DeviceClassWhere = "\"DeviceClass like '%s%%'\" % me.getDmdKey()"
    LocationWhere = "\"Location like '%s%%'\" % me.getDmdKey()"
    SystemWhere = "\"Systems like '%%|%s%%'\" % me.getDmdKey()"
    DeviceGroupWhere = "\"DeviceGroups like '%%|%s%%'\" % me.getDmdKey()"

    maintenanceProcedures = ("clean_old_events",)

    defaultResultFields = ("device", "component", "eventClass", "summary", 
                           "firstTime", "lastTime", "count" )

    defaultFields = ('eventState', 'severity', 'evid')

    defaultEventId = ('device', 'component', 'eventClass', 
                         'eventKey', 'severity')

    requiredEventFields = ('device', 'summary', 'severity')

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
        {'id':'host', 'type':'string', 'mode':'w'},
        {'id':'database', 'type':'string', 'mode':'w'},
        {'id':'port', 'type':'int', 'mode':'w'},
        {'id':'defaultWhere', 'type':'text', 'mode':'w'},
        {'id':'defaultOrderby', 'type':'text', 'mode':'w'},
        {'id':'defaultResultFields', 'type':'lines', 'mode':'w'},
        {'id':'statusTable', 'type':'string', 'mode':'w'},
        {'id':'detailTable', 'type':'string', 'mode':'w'},
        {'id':'logTable', 'type':'string', 'mode':'w'},
        {'id':'lastTimeField', 'type':'string', 'mode':'w'},
        {'id':'firstTimeField', 'type':'string', 'mode':'w'},
        {'id':'deviceField', 'type':'string', 'mode':'w'},
        {'id':'componentField', 'type':'string', 'mode':'w'},
        {'id':'severityField', 'type':'string', 'mode':'w'},
        {'id':'countField', 'type':'string', 'mode':'w'},
        {'id':'DeviceGroupField', 'type':'string', 'mode':'w'},
        {'id':'SystemField', 'type':'string', 'mode':'w'},
        {'id':'DeviceWhere', 'type':'string', 'mode':'w'},
        {'id':'DeviceResultFields', 'type':'lines', 'mode':'w'},
        {'id':'ComponentResultFields', 'type':'lines', 'mode':'w'},
        {'id':'EventClassWhere', 'type':'string', 'mode':'w'},
        {'id':'EventClassInstWhere', 'type':'string', 'mode':'w'},
        {'id':'DeviceClassWhere', 'type':'string', 'mode':'w'},
        {'id':'LocationWhere', 'type':'string', 'mode':'w'},
        {'id':'SystemWhere', 'type':'string', 'mode':'w'},
        {'id':'maintenanceProcedures', 'type':'lines', 'mode':'w'},
        {'id':'DeviceGroupWhere', 'type':'string', 'mode':'w'},
        {'id':'requiredEventFields', 'type':'lines', 'mode':'w'},
        {'id':'defaultEventId', 'type':'lines', 'mode':'w'},
        {'id':'defaultFields', 'type':'lines', 'mode':'w'},
        {'id':'timeout', 'type':'int', 'mode':'w'},
        {'id':'clearthresh', 'type':'int', 'mode':'w'},
        )
    
    factory_type_information = ( 
        { 
            'immediate_view' : 'editEventManager',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editEventManager'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Fields'
                , 'action'        : 'editEventManagerFields'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'history_edit'
                , 'name'          : 'History Fields'
                , 'action'        : 'editEventManagerHistoryFields'
                , 'permissions'   : ( "Manage DMD", )
                },
                { 'id'            : 'changes'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( permissions.view, )
                },
            )
          },
        )

    security = ClassSecurityInfo()
    

    def __init__(self, id, title='', username='root',
                 password='', database='events', host='127.0.0.1', port=3306,
                 defaultWhere='',defaultOrderby='',defaultResultFields=[]):
        self.id = id
        self.title = title
        self.username = username
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.defaultWhere = defaultWhere

        self.defaultOrderby="%s desc, %s desc" % (
                            self.severityField, self.lastTimeField)

        self._schema = {}
        self._fieldlist = []
        self._colors = ()
        self._ackedcolors = ()
        ObjectCache.__init__(self)
        self.initCache()

    #==========================================================================
    # Event query functions from IEventQuery
    #==========================================================================

    def getEventListME(self, me, **kwargs):
        where = self.lookupManagedEntityWhere(me)
        resultfields = self.lookupManagedEntityResultFields(me.event_key)
        return self.getEventList(resultFields=resultfields,where=where,**kwargs)

        
    def getEventList(self, resultFields=[], where="", orderby="", severity=None,
                    state=0, startdate=None, enddate=None, offset=0, rows=0):
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
            where = self._wand(where, "%s >= %s", self.severityField, severity)
            where = self._wand(where, "%s <= %s", self.stateField, state)
            if startdate:
                startdate, enddate = self._setupDateRange(startdate, enddate)
                where += " and %s >= '%s' and %s <= '%s'" % (
                         self.lastTimeField, startdate,
                         self.firstTimeField, enddate)
            select.append(where)
            if not orderby:
                orderby = self.defaultOrderby
            if orderby:
                select.append("order by")
                select.append(orderby)
            if rows:
                select.append("limit %d, %d" % (offset, rows))
            select.append(';')
            select = " ".join(select)
            #print select
            retdata = self.checkCache(select)
            if not retdata:
                db = self.connect()
                curs = db.cursor()
                curs.execute(select)
                retdata = []
                # iterate through the data results and convert to python
                # objects
                for row in curs.fetchall():
                    row = map(self.convert, resultFields, row)
                    evt = ZEvent(self, resultFields, row)
                    retdata.append(evt)
                db.close()
                self.addToCache(select, retdata)
                self.cleanCache()
            return retdata
        except:
            log.exception("Failure querying events")
            raise


    def getEventSummaryME(self, me, severity=1, state=1, prodState=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        try:
            where = self.lookupManagedEntityWhere(me)
            return self.getEventSummary(where, severity, state, prodState)
        except:
            log.exception("event summary for %s failed" % me.getDmdKey())
            raise


    def getEventSummary(self, where="", severity=1, state=1, prodState=None):
        """
        Return a list of tuples with number of events
        and the color of the severity that the number represents.
        """ 
        raise NotImplementedError


    def getEventDetail(self, evid=None, dedupid=None):
        """Return an EventDetail object for a particular event.
        """
        idfield = evid and "evid" or "dedupid"
        if not evid: evid = dedupid
        cachekey = '%s%s' % (idfield, evid)
        event = self.checkCache(cachekey)
        if event: return event
        db = self.connect()
        fields = self.getFieldList()
        selectevent = "select " 
        selectevent += ", ".join(fields)
        selectevent += " from %s where" % self.statusTable
        selectevent += " %s = '%s'" % (idfield, evid)
        if self.backend=="omnibus": selectevent += ";"
        
        #print selectevent
        curs = db.cursor()
        curs.execute(selectevent)
        evrow = curs.fetchone()
        if not evrow:
            raise (ZenEventNotFound,"Event evid %s not found" % evid)
        evdata = map(self.convert, fields, evrow)
        event = EventDetail(self, fields, evdata)
        event = event.__of__(self)

        selectdetail = "select name, value from %s where" % self.detailTable
        selectdetail += " evid = '%s'" % event.evid
        if self.backend=="omnibus": selectevent += ";"
        #print selectdetail
        curs.execute(selectdetail)
        event._details = curs.fetchall()

        selectlogs = "select userName, ctime, text"
        selectlogs += " from %s where" % self.logTable
        selectlogs += " evid = '%s' order by ctime desc" % event.evid
        if self.backend=="omnibus": selectevent += ";"
        #print selectlogs
        curs.execute(selectlogs)
        jrows = curs.fetchall()
        logs = []
        for row in jrows:
            user = self.cleanstring(row[0])
            date = self.dateString(row[1])
            text = row[2]
            logs.append((user, date, text))
        event._logs = logs
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
        elif isinstance(me, Organizer):
            return self.getOrganizerStatus(me, statusclass=statusclass, 
                                            **kwargs) 
        else:
            return self.getGenericStatus(me)


    def getGenericStatus(self, me):
        """Return status based on a where clause defined for the me event_type.
        No fancy caching done this might be a little slow if there are a lot
        of events.  Where clause is evaled 
        """
        where = self.lookupManagedEntityWhere(me)
        select = "select count(*) from %s where %s" % (self.statusTable, where)
        statusCount = self.checkCache(select)
        if not statusCount:
            db = self.connect()
            curs = db.cursor()
            #print select
            curs.execute(select)
            statusCount = curs.fetchone()[0]
            curs.close()
            db.close()
            self.addToCache(select,statusCount)
        return statusCount 
    
    
    def getOrganizerStatus(self, org, statusclass=None, severity=None, 
                           state=0, where=""):
        """see IEventStatus
        """
        orgfield = self.lookupManagedEntityField(org.event_key)
        select = "select %s from %s where " % (orgfield, self.statusTable)
        where = self._wand(where, "%s = '%s'", self.eventClassField,statusclass)
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        #print select
        statusCache = self.checkCache(select)
        if not statusCache:
            db = self.connect()
            curs = db.cursor()
            curs.execute(select)
            statusCache=[]
            orgdict={}
            for row in curs.fetchall():
                orgfield = self.cleanstring(row[0])
                if not orgfield: continue
                if orgfield.startswith("|"): orgfield = orgfield[1:]
                for orgname in orgfield.split("|"):
                    orgdict.setdefault(orgname, 0)
                    orgdict[orgname] += 1
            statusCache = orgdict.items()
            self.addToCache(select,statusCache)
            db.close()
        countevts = 0
        for key, value  in statusCache:
            if key.startswith(org.getOrganizerName()):
                countevts += value
        return countevts

    
    def getOrganizerStatusIssues(self, event_key,severity=4,state=0,
                                where="", limit=0):
        """Return list of tuples (org, count) for all organizers with events.
        """
        orgfield = self.lookupManagedEntityField(event_key)
        select = "select %s, count from %s where " % (orgfield,self.statusTable)
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        where = self._wand(where,"%s like '%s'",self.eventClassField,"/Status%")
        select += where
        statusCache = self.checkCache(select)
        if not statusCache:
            db = self.connect()
            curs = db.cursor()
            curs.execute(select)
            statusCache=[]
            orgdict={}
            for row in curs.fetchall():
                orgfield = self.cleanstring(row[0])
                if not orgfield: continue
                if orgfield.startswith("|"): orgfield = orgfield[1:]
                for orgname in orgfield.split("|"):
                    if not orgname: continue
                    count, total = orgdict.setdefault(orgname, (0,0))
                    count+=1
                    total+=row[1]
                    orgdict[orgname] = (count,total)
            statusCache = [ [n, c[0], int(c[1])] for n, c in orgdict.items() ]
            statusCache.sort(lambda x,y: cmp(x[1],y[1]))
            statusCache.reverse()
            if limit:
                statusCache = statusCache[:limit]
            self.addToCache(select,statusCache)
            db.close()
        return statusCache


    def getDevicePingIssues(self, state=2, limit=0):
        """Return devices with ping problems.
        """
        return self.getDeviceIssues(where="eventClass = '/Status/Ping'",
                                    severity=3,
                                    state=state,
                                    limit=limit)


    def getWmiConnIssues(self, state=2, limit=0):
        """Return devices with WMI connection failures.
        """
        where="severity>=3 and (eventClass = '/Status/Wmi/Conn'" \
                " or eventClass = '/Status/Ping')"
        return self.getDeviceIssues(where=where,state=state,limit=limit)
        

    def getDeviceStatusIssues(self, severity=4, state=1, limit=0):
        """Return only status issues.
        """
        return self.getDeviceIssues(where="eventClass like '/Status%'",
                            severity=severity, state=state, limit=limit)


    def getDeviceIssues(self,severity=1,state=0,where="",mincount=0,limit=0):
        """Return list of tuples (device, count, total) of events for
        all devices with events.
        """
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select = """select distinct device, count(device) as evcount, 
                    sum(count) from status where %s group by device
                    having evcount > %s""" % (where, mincount)
        statusCache = self.checkCache(select)
        if not statusCache:
            try:
                db = self.connect()
                curs = db.cursor()
                curs.execute(select)
                statusCache = [ [d,int(c),int(s)] for d,c,s in curs.fetchall() ]
                #statusCache = list(curs.fetchall())
                statusCache.sort(lambda x,y: cmp(x[1],y[1]))
                statusCache.reverse()
                if limit:
                    statusCache = statusCache[:limit]
                db.close()
            except:
                log.exception(select)
                raise
        return statusCache


    def getDeviceStatus(self, device, statclass=None, countField=None, 
                        severity=3, state=None, where=""):
        """see IEventStatus
        """
        if countField == None: countField = self.countField
        select = "select %s, %s from %s where " % (
                  self.deviceField, self.countField, self.statusTable)
        where = self._wand(where, "%s = '%s'", self.eventClassField, statclass)
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        #print select
        statusCache = self.checkCache(select)
        if not statusCache:
            try:
                db = self.connect()
                curs = db.cursor()
                curs.execute(select)
                statusCache = {}
                for dev, count in curs.fetchall():
                    dev = self.cleanstring(dev)
                    statusCache[dev] = count
                self.addToCache(select,statusCache)
                db.close()
            except:
                log.exception("status failed for device %s", device)
                return -1
        return statusCache.get(device, 0)


    def getHeartbeat(self, failures=True, simple=False, limit=0, db=None):
        """Return all heartbeat issues list of tuples (device, component, secs)
        """
        sel = """select device, component, lastTime from heartbeat """
        if failures:
            sel += "where DATE_ADD(lastTime, INTERVAL timeout SECOND) <= NOW();"
                    
        statusCache = self.checkCache(sel)
        cleanup = lambda : None
        if not statusCache:
            statusCache = []
            if db is None:
                db = self.connect()
                cleanup = db.close
            curs = db.cursor()
            curs.execute(sel)
            res = list(curs.fetchall())
            res.sort(lambda x,y: cmp(x[2],y[2]))
            devclass = self.getDmdRoot("Devices")
            for devname, comp, dtime in res:
                dtime = "%d" % int(time.time()-dtime.timeTime())
                dev = devclass.findDevice(devname)
                if dev and not simple:
                    alink = "<a href='%s'>%s</a>" % (
                            dev.getPrimaryUrlPath(), dev.id) 
                else: alink = devname
                statusCache.append([alink, comp, dtime])
            if limit:
                statusCache = statusCache[:limit]
            cleanup()
        return statusCache

        
    def getComponentStatus(self, device, component, statclass=None, 
                    countField=None, severity=3, state=1, where=""):
        """see IEventStatus
        """
        if countField == None: countField = self.countField
        select = "select %s, %s, %s from %s where "\
                  % (self.deviceField, self.componentField, countField,
                  self.statusTable)
        where = self._wand(where, "%s = '%s'", self.eventClassField, statclass)
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        statusCache = self.checkCache(select)
        if not statusCache:
            db = self.connect()
            curs = db.cursor()
            curs.execute(select)
            statusCache ={}
            for dev, comp, count in curs.fetchall():
                dev = self.cleanstring(dev)
                comp = self.cleanstring(comp)
                statusCache[dev+comp] = count
            self.addToCache(select,statusCache)
            db.close()
        return statusCache.get(device+component, 0)


    def getEventOwnerListME(self, me, severity=0, state=1):
        """Return list of event owners based on passed in managed entity.
        """
        try:
            where = self.lookupManagedEntityWhere(me)
            return self.getEventOwnerList(where, severity, state)
        except:
            log.exception("event summary for %s failed" % me.getDmdKey())
            raise


    def getEventOwnerList(self, where="", severity=0, state=1):
        """Return a list of userids that correspond to the events in where.
        select distinct ownerid from status where 
        device="win2k.confmon.loc" and eventState > 2
        """
        select ="select distinct ownerid from status where "
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        #print select
        statusCache = self.checkCache(select)
        if statusCache: return statusCache
        db = self.connect()
        curs = db.cursor()
        curs.execute(select)
        statusCache = [ uid[0] for uid in curs.fetchall() if uid[0] ]
        self.addToCache(select,statusCache)
        db.close()
        return statusCache


    def lookupManagedEntityWhere(self, me):
        """Lookup and build where clause for managed entity.
        """
        key = me.event_key + "Where"
        wheretmpl = getattr(aq_base(self), key, False)
        if not wheretmpl: 
            raise ValueError("no where fround for event_key %s" % 
                            me.event_key)
        return eval(wheretmpl,{'me':me})


    def lookupManagedEntityField(self, event_key):
        """Lookup database field for managed entity default is event_key.
        """
        key = event_key + "Field"
        return getattr(aq_base(self), key, event_key)


    def lookupManagedEntityResultFields(self, event_key):
        """Lookup and result fields for managed entity.
        """
        key = event_key + "ResultFields"
        return getattr(aq_base(self), key, self.defaultResultFields)


    def _wand(self, where, fmt, field, value):
        if value != None and where.find(field) == -1:
            if where: where += " and "
            where += fmt % (field, value)
        return where


    def _setupDateRange(self, startdate=DateTime.DateTime(), 
                              enddate=DateTime.DateTime()-1):
        """
        Make a start and end date range that is at least one day long.
        returns a start and end date as a proper database element.
        """
        if type(enddate) == types.StringType:
            enddate = DateTime.DateTime(enddate, datefmt='us')
        enddate = enddate.latestTime()
        if type(startdate) == types.StringType:
            startdate = DateTime.DateTime(startdate, datefmt='us')
        startdate = startdate.earliestTime()
        startdate = self.dateDB(startdate)
        enddate = self.dateDB(enddate)
        return startdate, enddate
    
   
    security.declareProtected('View','getDashboardInfo')
    def getDashboardInfo(self, simple=False, REQUEST=None):
        """Return a dictionary that has all info for the dashboard.
        """
        data = self.checkCache("dashboardinfo%s" % simple)
        if data: return data
        data = {}
        devices = [d[0] for d in self.getDeviceIssues(
                            severity=4, state=1, limit=100)]
        devdata = []
        devclass = self.getDmdRoot("Devices")

        def evtprep(evts):
            evtsdata = "%d/%d" % (evts[1],evts[2])
            if evts[1]==evts[2] or evts[2]==0:
                return evtsdata
            else:
                return {'cssclass':evts[0], 'data':evtsdata}

        for devname in devices:
            dev = devclass.findDevice(devname)
            if dev:
                if dev.productionState < self.prodStateDashboardThresh: 
                    continue
                if simple:
                    alink = devname
                else:
                    alink = "<a href='%s'>%s</a>" % (
                        dev.getPrimaryUrlPath()+"/viewEvents", dev.id )
                owners = ", ".join(dev.getEventOwnerList(severity=4))
                evtsum = dev.getEventSummary(severity=4)
            else:
                # handle event from device that isn't in dmd
                alink = devname
                owners = ""
                evtsum = self.getEventSummary("device='%s'"%devname,severity=4)
            evts = [alink, owners]
            evts.extend(map(evtprep, evtsum))
            devdata.append(evts)
        devdata.sort()
        data['deviceevents'] = devdata

        sysroot = self.getDmdRoot("Systems")
        sysdata = []
        for sys in sysroot.children():
            if simple:
                alink = sys.getOrganizerName()
            else:
                alink = "<a href='%s'>%s</a>" % (
                        sys.getPrimaryUrlPath()+"/viewEvents",
                        sys.getOrganizerName())
            evts = [ alink ]
            evts.extend(map(evtprep, sys.getEventSummary(prodState=1000)))
            sysdata.append(evts)
        
        sysdata.sort()
        data['systemevents'] = sysdata
        data['heartbeat'] = self.getHeartbeat()
        self.addToCache("dashboardinfo", data)
        self.cleanCache()
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Cache-Control', 'no-cache')
            REQUEST.RESPONSE.setHeader('Expires', '-1')
            REQUEST.RESPONSE.setHeader("Pragma", "no-cache")
        return data

    security.declareProtected('View','getJSONEventsInfo')
    def getJSONEventsInfo(self, simple=False, REQUEST=None):
        """
        Event data in JSON format.
        """
        
    #==========================================================================
    # Event sending functions
    #==========================================================================

    security.declareProtected('Send Events', 'sendEvents')
    def sendEvents(self, events):
        """Send a group of events to the backend.
        """
        count = 0
        db = self.connect()
        for event in events:
            try:
                self.sendEvent(event, db)
                count += 1
            except Exception, ex:
                log.exception(ex)
        db.close()
        return count


    security.declareProtected('Send Events', 'sendEvent')
    def sendEvent(self, event, db=None):
        """Send an event to the backend.
        """
        raise NotImplementedError
            

    #==========================================================================
    # Schema management functions
    #==========================================================================

    def convert(self, field, value):
        """Perform convertion of value coming from database value if nessesary.
        """
        value = self.cleanstring(value)
        #FIXME this is commented out because we often need severity as a
        # number (like in ZEvent.getCssClass) and sorting.  Need to have
        # both fields at some point
        #if field == self.severityField:
        #    idx = len(self.severityConversions) - value
        #    value = self.severityConversions[idx][0]
        if self.isDate(field):
            value = self.dateString(value)
        return value


    security.declareProtected("View", "getFieldList")
    def getFieldList(self):
        """Return a list of all fields in the status table of the  backend.
        """
        if not self._fieldlist:
            db = self.connect()
            try:
                self.loadSchema(db)
            finally:
                db.close()
        return self._fieldlist


    def getEventStates(self):
        """Return a list of possible event states.
        """
        return self.eventStateConversions


    security.declareProtected('View','getSeverities')
    def getSeverities(self):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        return self.severityConversions

    def getSeverityString(self, severity):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        try:
            return self.severities[severity]
        except IndexError:
            return "Unknown"

   
    def getStatusCssClass(self, status):
        if status < 0: status = "unknown"
        elif status > 3: status = 3
        return "zenstatus_%s" % status


    def getEventCssClass(self, severity, acked=False):
        """return the css class name to be used for this event.
        """
        value = severity < 0 and "unknown" or severity
        acked = acked and "acked" or "noack"
        return "zenevents_%s_%s" % (value, acked)


    def isDate(self, colName):
        """Check to see if a column is of type date.
        """
        if not self._schema:
            self.getFieldList()
        return self._schema.get(colName, False)


    def dateString(self, value):
        """Convert a date from database format to string.
        """
        if isinstance(value, DateTime.DateTime): 
            value = value.timeTime() 
        return Time.LocalDateTime(value)
        


    def dateDB(self, value):
        """Convert a date to its database format.
        """
        if isinstance(value, DateTime.DateTime):
            return "%.3f" % value.timeTime()
        elif type(value) == types.StringTypes:
            return "%.3f" % DateTime.DateTime(value).timeTime()
        return value


    def escape(self, value):
        """Prepare string values for db by escaping special characters.
        """
        raise NotImplementedError


    def loadSchema(self, db):
        """Load schema from database. If field is a date set value to true."""
        schema = {}
        fieldlist = []
        sql = "describe %s;" % self.statusTable
        curs = db.cursor()
        try:
            curs.execute(sql)
            for row in curs.fetchall():
                fieldlist.append(row[0])
                col = self.cleanstring(row[0])
                if self.backend == "omnibus":
                    type = row[1] in (1, 4, 7, 8) #different date types
                elif self.backend == "mysql":
                    type = row[1] in ("datetime", "timestamp", "double")
                schema[col] = type
            if schema: self._schema = schema 
            self._fieldlist = fieldlist
        finally:
            curs.close()


    def eventControls(self):
        """Are there event controls on this event list.
        """
        if self.isManager() and self.statusTable == "status":
            return 1
        return 0


    security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        "Delete the given event ids"
        if type(evids) == type(''):
            evids = [evids]
        if evids: 
            delete = "delete from status where evid in ("
            delete += ",".join([ "'%s'" % evid for evid in evids]) + ")"
            db = self.connect()
            curs = db.cursor()
            curs.execute(delete);
            db.close()
            self.clearCache()
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteAllEvents')
    def manage_deleteAllEvents(self, devname, REQUEST=None):
        delete = 'delete from status where device = "%s"' % devname
        db = self.connect()
        curs = db.cursor()
        curs.execute(delete);
        db.close()
        self.clearCache()
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, devname, REQUEST=None):
        if devname:
            delete = "delete from heartbeat where device = '%s'" % devname
            db = self.connect()
            curs = db.cursor()
            curs.execute(delete);
            db.close()
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    def manage_ackEvents(self, evids=(), REQUEST=None):
        "Ack the given event ids"
        if type(evids) == type(''):
            evids = [evids]
        return self.manage_setEventStates(1 , evids, REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        if eventState and evids: 
            eventState = int(eventState)
            userid = ""
            if eventState > 0: userid = getSecurityManager().getUser()
            delete = "update status set eventState=%s, ownerid='%s' " % (
                        eventState, userid)
            delete += "where evid in (" 
            delete += ",".join([ "'%s'" % evid for evid in evids]) + ")"
            #print delete
            db = self.connect()
            curs = db.cursor()
            curs.execute(delete);
            db.close()
            self.clearCache()
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_createEventMap(self, eventClass=None, evids=(), REQUEST=None):
        """Create an event map from an event or list of events.
        """
        evclass = None
        evmap = None
        if eventClass and evids: 
            evclass = self.getDmdRoot("Events").getOrganizer(eventClass)
            sel = """select eventClassKey, eventClass, message 
                    from %s where evid in ('%s')"""
            sel = sel % (self.statusTable, "','".join(evids))
            db = self.connect()
            curs = db.cursor()
            curs.execute(sel);
            for row in curs.fetchall():
                evclasskey, curevclass, msg = row
                if curevclass != Unknown: continue
                evmap = evclass.createInstance(evclasskey)
                evmap.eventClassKey = evclasskey
                evmap.example = msg
            db.close()
        if REQUEST: 
            if len(evids) == 1 and evmap: return evmap()
            elif evclass and evmap: return evclass()


    security.declareProtected('Manage EventManager','manage_refreshConversions')
    def manage_refreshConversions(self, REQUEST=None):
        """get the conversion information from the omnibus server"""
        assert(self == self.dmd.ZenEventManager)
        db = self.connect()
        self.loadSchema(db)
        self.dmd.ZenEventHistory.loadSchema(db)
        db.close()
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage EventManager','manage_editCache')
    def manage_editCache(self, timeout=5, clearthresh=20, REQUEST=None):
        """Reset cache values"""
        self.timeout = int(timeout)
        self.clearthresh = int(clearthresh)
        if REQUEST:
            message = "Cache parameters set"
            return self.editCache(self, REQUEST, manage_tabs_message=message)


    security.declareProtected('Manage EventManager','manage_clearCache')
    def manage_clearCache(self, REQUEST=None):
        """Reset cache values"""
        assert(self == self.dmd.ZenEventManager)
        self.cleanCache(force=1)
        self.dmd.ZenEventHistory.cleanCache(force=1)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage EventManager','manage_editEventManager')
    def manage_editEventManager(self, REQUEST=None):
        ''' Call zmanage_editProperties then take care of saving a few
        values to ZenEventHistory
        '''
        assert(self == self.dmd.ZenEventManager)
        self.zmanage_editProperties(REQUEST)
        self.dmd.ZenEventHistory.timeout = REQUEST['history_timeout']
        self.dmd.ZenEventHistory.clearthresh = REQUEST['history_clearthresh']
        self.dmd.ZenEventHistory.username = self.dmd.ZenEventManager.username
        self.dmd.ZenEventHistory.password = self.dmd.ZenEventManager.password
        self.dmd.ZenEventHistory.database = self.dmd.ZenEventManager.database
        self.dmd.ZenEventHistory.host = self.dmd.ZenEventManager.host
        self.dmd.ZenEventHistory.port = self.dmd.ZenEventManager.port
        if REQUEST: return self.callZenScreen(REQUEST)

   
    security.declareProtected('Manage EventManager','manage_clearHeartbeats')
    def manage_clearHeartbeats(self, REQUEST=None):
        """truncate heartbeat table"""
        db = self.connect()
        cursor = db.cursor()
        try:
            sql = 'truncate table heartbeat'
            cursor.execute(sql)
        finally:
            cursor.close()
            db.close()
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage EventManager','zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        ''' Need to handle editing of history event fields differently
        '''
        assert(self == self.dmd.ZenEventManager)
        if REQUEST.get('zenScreenName', '') == 'editEventManagerHistoryFields':
            obj = self.dmd.ZenEventHistory
        else:
            obj = self
        ZenModelItem.zmanage_editProperties(obj, REQUEST)
        if REQUEST: return self.callZenScreen(REQUEST)
    
    #==========================================================================
    # Utility functions
    #==========================================================================

    def _genuuid(self):
        """globally unique id based on timestamp, fqdn, and random number.
        """
        d=datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        r = "%04d" % random.randint(0, 1000)
        return d+str(d.microsecond)+r+self.FQDNID


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


