###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

"""EventManagerBase

$Id: NcoManager.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import time
import types
import random
import simplejson
random.seed()
import logging
log = logging.getLogger("zen.Events")

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Globals import InitializeClass
from Globals import DTMLFile
from Acquisition import aq_base, aq_parent
import DateTime
from AccessControl import Permissions as permissions

from Products.ZenUtils.ObjectCache import ObjectCache
from Products.ZenModel.Organizer import Organizer

from interfaces import IEventList, IEventStatus, ISendEvents

from ZEvent import ZEvent
from EventDetail import EventDetail
from BetterEventDetail import BetterEventDetail
from EventCommand import EventCommand
from Exceptions import *

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenEvents.ZenEventClasses import Status_Ping, Status_Wmi_Conn
import StringIO
import csv

from ZenEventClasses import Unknown

import time

from DbAccessBase import DbAccessBase


def evtprep(evts):
    evtsdata = "%d/%d" % (evts[1],evts[2])
    if evts[1]==evts[2] or evts[2]==0:
        return {'cssclass':evts[0] + " empty thin",
                'data':evtsdata}
    else:
        return {'cssclass':evts[0], 'data':evtsdata}


class EventManagerBase(ZenModelRM, ObjectCache, DbAccessBase):
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

    eventActions = ('status', 'history', 'drop')

    severityConversions = (
        ('Critical', 5),
        ('Error', 4),
        ('Warning', 3),
        ('Info', 2),
        ('Debug', 1),
        ('Clear', 0),
    )
    severities = dict([(b, a) for a, b in severityConversions])

    priorityConversions = (
        ('None', -1),
        ('Emergency', 0),
        ('Alert', 1),
        ('Critical', 2),
        ('Error', 3),
        ('Warning', 4),
        ('Notice', 6),
        ('Info', 8),
        ('Debug', 10),
    )
    priorities = dict([(b, a) for a, b in priorityConversions])

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

    defaultResultFields = ("device", "component", "eventClass", "summary",
                           "firstTime", "lastTime", "count" )

    defaultFields = ('eventState', 'severity', 'evid')

    defaultEventId = ('device', 'component', 'eventClass',
                         'eventKey', 'severity')

    requiredEventFields = ('device', 'summary', 'severity')

    refreshConversionsForm = DTMLFile('dtml/refreshNcoProduct', globals())
    
    defaultAvailabilityDays = 7
    defaultPriority = 3
    eventAgingHours = 4
    eventAgingSeverity = 4
    
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
        {'id':'DeviceGroupWhere', 'type':'string', 'mode':'w'},
        {'id':'requiredEventFields', 'type':'lines', 'mode':'w'},
        {'id':'defaultEventId', 'type':'lines', 'mode':'w'},
        {'id':'defaultFields', 'type':'lines', 'mode':'w'},
        {'id':'timeout', 'type':'int', 'mode':'w'},
        {'id':'clearthresh', 'type':'int', 'mode':'w'},
        {'id':'defaultAvailabilityDays', 'type':'int', 'mode':'w'},
        {'id':'defaultPriority', 'type':'int', 'mode':'w'},
        {'id':'eventAgingHours', 'type':'int', 'mode':'w'},
        {'id':'eventAgingSeverity', 'type':'int', 'mode':'w'},
        )

    _relations =  (
        ("commands", ToManyCont(ToOne, "Products.ZenEvents.EventCommand", "eventManager")),
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
                { 'id'            : 'commands'
                , 'name'          : 'Commands'
                , 'action'        : 'listEventCommands'
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
    

    def __init__(self, id, title='', hostname='localhost', username='root',
                 password='', database='events', port=3306,
                 defaultWhere='',defaultOrderby='',defaultResultFields=[]):
        self.id = id
        self.title = title
        self.username=username
        self.password=password
        self.database=database
        self.host=hostname
        self.port=port
        DbAccessBase.__init__(self)
        
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
                    state=0, startdate=None, enddate=None, offset=0, rows=0,
                    getTotalCount=False, filter=""):
        """see IEventList.
        """
        try:
            if not resultFields:
                resultFields = self.defaultResultFields
            resultFields = list(resultFields)
            resultFields.extend(self.defaultFields)
            calcfoundrows = ''
            if getTotalCount: 
                calcfoundrows = 'SQL_CALC_FOUND_ROWS'
            select = ["select ", calcfoundrows, ','.join(resultFields),
                        "from %s where" % self.statusTable ]
                        
            if not where:
                where = self.defaultWhere
            where = self._wand(where, "%s >= %s", self.severityField, severity)
            where = self._wand(where, "%s <= %s", self.stateField, state)
            if filter:
                where += ' and (%s) ' % (' or '.join(['%s LIKE "%%%s%%"' % (
                            x, filter) for x in resultFields]))
                log.info(where)
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
            if getTotalCount: 
                try: retdata, totalCount = self.checkCache(select)
                except TypeError: retdata, totalCount = self.checkCache(select), 100
            else: retdata = self.checkCache(select)
            if not False:
                conn = self.connect()
                try:
                    curs = conn.cursor()
                    log.info(select)
                    curs.execute(select)
                    retdata = []
                    # iterate through the data results and convert to python
                    # objects
                    for row in curs.fetchall():
                        row = map(self.convert, resultFields, row)
                        evt = ZEvent(self, resultFields, row)
                        retdata.append(evt)
                    if getTotalCount:
                        curs.execute("SELECT FOUND_ROWS()")
                        totalCount = curs.fetchone()[0]
                finally: self.close(conn)
                if getTotalCount: self.addToCache(select, (retdata, totalCount))
                else: self.addToCache(select, retdata)
                self.cleanCache()
            if getTotalCount: 
                return retdata, totalCount
            else: return retdata
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


    def getEventDetailFromStatusOrHistory(self, evid=None, dedupid=None,
                                                            better=False):
        try:
            event = self.dmd.ZenEventManager.getEventDetail(
                                                    evid, dedupid, better)
        except ZenEventNotFound:
            event = self.dmd.ZenEventHistory.getEventDetail(evid, dedupid,
                                                                        better)
        return event

    def getEventDetail(self, evid=None, dedupid=None, better=False):
        """Return an EventDetail object for a particular event.
        """
        idfield = evid and "evid" or "dedupid"
        if not evid: evid = dedupid
        cachekey = '%s%s' % (idfield, evid)
        event = self.checkCache(cachekey)
        if event: return event
        fields = self.getFieldList()
        selectevent = "select " 
        selectevent += ", ".join(fields)
        selectevent += " from %s where" % self.statusTable
        selectevent += " %s = '%s'" % (idfield, evid)
        if self.backend=="omnibus": selectevent += ";"
        conn = self.connect()
        try:
            curs = conn.cursor()
            curs.execute(selectevent)
            evrow = curs.fetchone()
            if not evrow:
                raise (ZenEventNotFound,"Event evid %s not found" % evid)
            evdata = map(self.convert, fields, evrow)
            if better:
                event = BetterEventDetail(self, fields, evdata)
            else:
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
        finally: self.close(conn)
        
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
            conn = self.connect()
            try:
                curs = conn.cursor()
                #print select
                curs.execute(select)
                statusCount = curs.fetchone()[0]
            finally: self.close(conn)

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
            conn = self.connect()
            try:
                curs = conn.cursor()
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
            finally: self.close(conn)
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
            conn = self.connect()
            try:
                curs = conn.cursor()
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
            finally: self.close(conn)
        return statusCache


    def getDevicePingIssues(self, state=2, limit=0):
        """Return devices with ping problems.
        """
        return self.getDeviceIssues(where="eventClass = '%s'" % Status_Ping,
                                    severity=3,
                                    state=state,
                                    limit=limit)


    def getWmiConnIssues(self, state=2, limit=0):
        """Return devices with WMI connection failures.
        """
        where="severity>=3 and (eventClass = '%s' or eventClass = '%s')" % (
								Status_Wmi_Conn, Status_Ping)
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
                conn = self.connect()
                try:
                    curs = conn.cursor()
                    curs.execute(select)
                    statusCache = [ [d,int(c),int(s)] for d,c,s in curs.fetchall() ]
                    #statusCache = list(curs.fetchall())
                    statusCache.sort(lambda x,y: cmp(x[1],y[1]))
                    statusCache.reverse()
                    if limit:
                        statusCache = statusCache[:limit]
                finally: self.close(conn)
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
                conn = self.connect()
                try:
                    curs = conn.cursor()
                    curs.execute(select)
                    statusCache = {}
                    for dev, count in curs.fetchall():
                        dev = self.cleanstring(dev)
                        statusCache[dev] = count
                    self.addToCache(select,statusCache)
                finally: self.close(conn)
            except:
                log.exception("status failed for device %s", device)
                return -1
        return statusCache.get(device, 0)


    def defaultAvailabilityStart(self):
        return Time.USDate(time.time() - 60*60*24*self.defaultAvailabilityDays)


    def defaultAvailabilityEnd(self):
        return Time.USDate(time.time())


    def getAvailability(self, state, **kw):
        import Availability
        for name in "device", "component", "eventClass":
            if hasattr(state, name):
                kw.setdefault(name, getattr(state, name))
        try:
            kw.setdefault('severity',
                        dict(self.severityConversions)[state.severity])
        except (ValueError, KeyError):
            pass
        for name in "startDate", "endDate":
            if hasattr(state, name):
                kw.setdefault(name, Time.ParseUSDate(getattr(state, name)))
        kw.setdefault('startDate',
                      time.time() - 60*60*24*self.defaultAvailabilityDays)
        return Availability.query(self.dmd, **kw)


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
            conn = self.connect()
            try:
                curs = conn.cursor()
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
            finally: self.close(conn)
        return statusCache

        
    def getAllComponentStatus(self,
                              statclass,
                              countField=None,
                              severity=3,
                              state=1,
                              where=""):
        "Fetch the counts on all components matching statClass"
        if countField == None: countField = self.countField
        select = "select %s, %s, %s from %s where "\
                  % (self.deviceField, self.componentField, countField,
                     self.statusTable)
        where = self._wand(where, "%s = '%s'", self.eventClassField, statclass)
        where = self._wand(where, "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        select += where
        conn = self.connect()
        try:
            curs = conn.cursor()
            curs.execute(select)
            result = {}
            for dev, comp, count in curs.fetchall():
                dev = self.cleanstring(dev)
                comp = self.cleanstring(comp)
                result[dev,comp] = 0
            return result 
        finally:
            self.close(conn)


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
            conn = self.connect()
            try:
                curs = conn.cursor()
                curs.execute(select)
                statusCache ={}
                for dev, comp, count in curs.fetchall():
                    dev = self.cleanstring(dev)
                    comp = self.cleanstring(comp)
                    statusCache[dev+comp] = count
                self.addToCache(select,statusCache)
            finally: self.close(conn)
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
        conn = self.connect()
        try:
            curs = conn.cursor()
            curs.execute(select)
            statusCache = [ uid[0] for uid in curs.fetchall() if uid[0] ]
            self.addToCache(select,statusCache)
        finally: self.close(conn)
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
        data['systemevents'] = self.getOrganizerSummary(
                                        'Systems','viewEvents', simple)
        data['heartbeat'] = self.getHeartbeat()
        data['deviceevents'] = self.getDeviceDashboard(simple)
        self.addToCache("dashboardinfo", data)
        self.cleanCache()
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Cache-Control', 'no-cache')
            REQUEST.RESPONSE.setHeader('Expires', '-1')
            REQUEST.RESPONSE.setHeader("Pragma", "no-cache")
        return data


    def getDeviceDashboard(self, simple=False):
        """return device info for bad device to dashboard"""
        devices = [d[0] for d in self.getDeviceIssues(
                            severity=4, state=1, limit=100)]
        devdata = []
        devclass = self.getDmdRoot("Devices")
        for devname in devices:
            dev = devclass.findDevice(devname)
            if dev:
                if dev.productionState < self.prodStateDashboardThresh:
                    continue
                if dev.priority < self.priorityDashboardThresh:
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
        return devdata


    def getOrganizerSummary(self, rootname='Systems',template='',simple=False):
        """Return systems info for dashboard."""
        root = self.getDmdRoot(rootname)
        data = []
        for sys in root.children():
            if simple:
                alink = sys.getOrganizerName()
            else:
                alink = "<a href='%s/%s'>%s</a>" % (
                        sys.getPrimaryUrlPath(),template,
                        sys.getOrganizerName())
            evts = [ alink ]
            evts.extend(map(evtprep, sys.getEventSummary(prodState=1000)))
            data.append(evts)
        data.sort()
        return data
        

    def getOrganizerDashboard(self):
        return {
                'systemevents': self.getOrganizerSummary(),
                'locationevents': self.getOrganizerSummary('Locations')
        }


    def getSummaryDashboard(self, REQUEST=None):
        '''Build summary of serveral zope servers'''
        import urllib, re
        user = 'admin'; pw = 'zenoss'
        servernames = ['zenoss', 'tilde']
        dashurl = "<a href='http://%s:8080/zport/dmd/'>%s</a>"
        sumurl = 'http://%s:%s@%s:8080/zport/dmd/Systems/getEventSummary'
        infourl = 'http://%s:%s@%s:8080/zport/dmd/ZenEventManager/getDashboardInfo'
        info = {'deviceevents': [], 'systemevents': [], 'heartbeat': []}

        def getData(user, pw, urlfmt):
            data = ''
            try:
                url = urlfmt % (user, pw, s)
                data = urllib.urlopen(url).read()
                if re.search('zenevents_5_noack', data): 
                    return data
            except IOError: pass

        zenossdata = []
        for s in servernames:
                data = getData(user, pw, sumurl)
                if not data: continue
                evts = [ dashurl % (s, s) ] 
                evts.extend(map(evtprep, eval(data)))
                zenossdata.append(evts)
        zenossdata.sort()
        info['systemevents'] = zenossdata
        for s in servernames:
            data = getData(user, pw, infourl)
            if not data: continue
            data = eval(data)
            info['deviceevents'].extend(data['deviceevents'])
            info['heartbeat'].extend(data['heartbeat'])
            
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Cache-Control', 'no-cache')
            REQUEST.RESPONSE.setHeader('Expires', '-1')
            REQUEST.RESPONSE.setHeader("Pragma", "no-cache")
        return info
            
    security.declareProtected('View','getJSONHistoryEventsInfo')
    def getJSONHistoryEventsInfo(self, **kwargs):
        kwargs['history'] = True
        return self.getJSONEventsInfo(**kwargs)

    security.declareProtected('View','getJSONEventsInfo')
    def getJSONEventsInfo(self, offset=0, count=50, fields=[], 
                          getTotalCount=True, 
                          filter='', severity=2, state=1, 
                          orderby='', REQUEST=None):
        """ Event data in JSON format.
        """
        argnames = ('offset count getTotalCount ' 
                   'filter severity state orderby').split()
        myargs = {}
        for arg in argnames:
            myargs[arg] = eval(arg)
        if not fields: fields = self.defaultResultFields
        myargs['resultFields'] = fields
        myargs['rows'] = myargs['count']; del myargs['count']
        if myargs['orderby']=='count': myargs['orderby']=='rows';
        data, totalCount = self.getEventList(**myargs)
        results = [x.getDataForJSON(fields) + [x.getCssClass()] for x in data]
        return simplejson.dumps((results, totalCount))

    security.declareProtected('View','getJSONFields')
    def getJSONFields(self, fields=[], REQUEST=None):
        if not fields:
            fields = self.defaultResultFields
        lens = map(self.getAvgFieldLength, fields)
        total = sum(lens)
        lens = map(lambda x:x/total*100, lens)
        zipped = zip(fields, lens)
        return simplejson.dumps(zipped)

    def getAvgFieldLength(self, fieldname):
        conn = self.connect()
        try:
            curs = conn.cursor()
            selstatement = ("SELECT AVG(CHAR_LENGTH(mycol)) FROM (SELECT %s AS "
                            "mycol FROM %s LIMIT 50) AS a;") % (fieldname,
                                self.statusTable)
            curs.execute(selstatement)
            avglen = curs.fetchone()
        finally: self.close(conn)
        if not avglen: return 0.
        else: return float(avglen[0])

        
    #==========================================================================
    # Event sending functions
    #==========================================================================

    security.declareProtected('Send Events', 'sendEvents')
    def sendEvents(self, events):
        """Send a group of events to the backend.
        """
        count = 0
        for event in events:
            try:
                self.sendEvent(event)
                count += 1
            except Exception, ex:
                log.exception(ex)
        return count


    security.declareProtected('Send Events', 'sendEvent')
    def sendEvent(self, event):
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
        if not getattr(self, '_fieldlist', None):
            self.loadSchema()
        return self._fieldlist

    def getEventStates(self):
        """Return a list of possible event states.
        """
        return self.eventStateConversions

    def getEventActions(self):
        """Return a list of possible event actions.
        """
        return self.eventActions

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

    def getPriorities(self):
        """Return a list of tuples of priorities [('Warning', 3), ...] 
        """
        return self.priorityConversions

    def getPriorityString(self, priority):
        """Return the priority name 
        """
        try:
            return self.priorities[priority]
        except IndexError:
            return "Unknown"

    def getStatusCssClass(self, status):
        if status < 0: status = "unknown"
        elif status > 3: status = 3
        return "zenstatus_%s" % status
        
        
    def getStatusImgSrc(self, status):
        ''' Return the img source for a status number
        '''
        if status < 0:
            src = 'magenta'
        if status == 0:
            src = 'green'
        elif status == 1:
            src = 'yellow'
        elif status == 2:
            src = 'yellow'
        else:
            src = 'red'
        return 'misc_/SiteScopeParser/%sball_img' % src


    def getEventCssClass(self, severity, acked=False):
        """return the css class name to be used for this event.
        """
        value = severity < 0 and "unknown" or severity
        acked = acked and "acked" or "noack"
        return "zenevents_%s_%s %s" % (value, acked, acked)


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


    def loadSchema(self):
        """Load schema from database. If field is a date set value to true."""
        schema = {}
        fieldlist = []
        sql = "describe %s;" % self.statusTable
        conn = self.connect()
        try:
            curs = conn.cursor()
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
        finally: self.close(conn)


    def eventControls(self):
        """Are there event controls on this event list.
        """
        if self.isManager() and self.statusTable in ["status","history"]:
            return 1
        return 0

    def updateEvents(self, stmt, whereClause, reason,
                     table="status", toLog=True):
        userId = getSecurityManager().getUser().getId()
        insert = 'INSERT INTO log (evid, userName, text) ' + \
                 'SELECT evid, "%s", "%s" ' % (userId, reason) + \
                 'FROM %s ' % table + whereClause
        query = stmt + ' ' + whereClause
        conn = self.connect()
        try:
            curs = conn.cursor()
            if toLog: curs.execute(insert)
            curs.execute(query)
        finally: self.close(conn)
        self.clearCache()
        self.manage_clearCache()
        
    security.declareProtected('Manage Events','manage_addEvent')
    def manage_addEvent(self, REQUEST=None):
        ''' Create an event from user supplied data
        '''
        eventDict = dict(
            summary = REQUEST['summary'],
            device = REQUEST['device'],
            component = REQUEST['component'],
            severity = REQUEST['severity'],
            eventClassKey = REQUEST['eventClassKey'],
            eventClass = REQUEST['eclass'],
            )
        evid = self.sendEvent(eventDict)
        if REQUEST:
            REQUEST['RESPONSE'].redirect('/zport/dmd/Events/viewEvents')

    def deleteEvents(self, whereClause, reason):
        self.updateEvents('DELETE FROM status', whereClause, reason)

    security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        "Delete the given event ids"
        if type(evids) == type(''):
            evids = [evids]
        if evids:
            evids = ",".join([ "'%s'" % evid for evid in evids])
            whereClause = ' where evid in (%s)' % evids
            self.deleteEvents(whereClause, 'Deleted by user')
        if REQUEST: return self.callZenScreen(REQUEST)

    def undeleteEvents(self, whereClause, reason):
        fields = ','.join( self.getFieldList() )
        # We want to blank clearid
        fields = fields.replace('clearid','NULL')
        self.updateEvents(  'INSERT status ' + \
                            'SELECT %s FROM history' % fields, \
                            whereClause, reason, 'history', toLog=False)
        self.updateEvents( 'DELETE FROM history', whereClause, \
                            reason, 'history')

    security.declareProtected('Manage Events','manage_undeleteEvents')
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        "Move the given event ids into status and delete from history"
        if type(evids) == type(''):
            evids = [evids]
        if evids:
            l = len(evids)
            evids = ",".join([ "'%s'" % evid for evid in evids])
            whereClause = ' where evid in (%s)' % evids
            self.undeleteEvents(whereClause, 'Undeleted by user')
        if REQUEST: 
            REQUEST['message'] = "%s events undeleted." % l
            return self.callZenScreen(REQUEST)

    security.declareProtected('Manage Events','manage_deleteAllEvents')
    def manage_deleteAllEvents(self, devname, REQUEST=None):
        "Delete the events for a given Device (used for deleting the device"
        whereClause = 'where device = "%s"' % devname
        self.deleteEvents(whereClause, 'Device deleted')
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, devname, REQUEST=None):
        if devname:
            delete = "delete from heartbeat where device = '%s'" % devname
            conn = self.connect()
            try:
                curs = conn.cursor()
                curs.execute(delete);
            finally: self.close(conn)
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
            update = "update status set eventState=%s, ownerid='%s' " % (
                        eventState, userid)
            whereClause = "where evid in (" 
            whereClause += ",".join([ "'%s'" % evid for evid in evids]) + ")"
            reason = 'Event state changed to '
            try:
                reason += self.eventStateConversions[eventState][0]
            except KeyError:
                reason += 'unknown (%d)' % eventState
            self.updateEvents(update, whereClause, reason)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_createEventMap(self, eventClass=None, evids=(),
                              REQUEST=None):
        """Create an event map from an event or list of events.
        """
        evclass = None
        evmap = None
        if eventClass and evids:
            evclass = self.getDmdRoot("Events").getOrganizer(eventClass)
            sel = """select eventClassKey, eventClass, message 
                    from %s where evid in ('%s')"""
            sel = sel % (self.statusTable, "','".join(evids))
            conn = self.connect()
            try:
                curs = conn.cursor()
                curs.execute(sel);
                for row in curs.fetchall():
                    evclasskey, curevclass, msg = row
                    if curevclass != Unknown or not evclasskey: continue
                    evmap = evclass.createInstance(evclasskey)
                    evmap.eventClassKey = evclasskey
                    evmap.example = msg
            finally: self.close(conn)
        if REQUEST:
            if len(evids) == 1 and evmap: return evmap()
            elif evclass and evmap: return evclass()


    security.declareProtected('Manage EventManager','manage_refreshConversions')
    def manage_refreshConversions(self, REQUEST=None):
        """get the conversion information from the omnibus server"""
        assert(self == self.dmd.ZenEventManager)
        self.loadSchema()
        self.dmd.ZenEventHistory.loadSchema()
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
        conn = self.connect()
        try:
            curs = conn.cursor()
            sql = 'truncate table heartbeat'
            curs.execute(sql)
        finally: self.close(conn)
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
        ZenModelRM.zmanage_editProperties(obj, REQUEST)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage EventManager', 'manage_addLogMessage')
    def manage_addLogMessage(self, evid=None, message='', REQUEST=None):
        'Add a log message to an event'
        if not evid:
            return
        userId = getSecurityManager().getUser().getId()
        conn = self.connect()
        try:
            curs = conn.cursor()
            insert = 'INSERT INTO log (evid, userName, text) '
            insert += 'VALUES ("%s", "%s", "%s")' % (evid,
                                                     userId,
                                                     conn.escape_string(message))
            curs.execute(insert)
        finally: self.close(conn)
        self.clearCache('evid' + evid)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage EventManager', 'manage_addCommand')
    def manage_addCommand(self, id, REQUEST=None):
        "add a new EventCommand"
        ec = EventCommand(id)
        self.commands._setObject(id, ec)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage EventManager', 'manage_deleteCommands')
    def manage_deleteCommands(self, ids, REQUEST=None):
        "add a new EventCommand"
        for id in ids:
            try:
                self.commands._delObject(id)
            except (AttributeError, KeyError):
                pass
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
