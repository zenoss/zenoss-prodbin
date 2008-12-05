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

__doc__ = """EventManagerBase
Data connector to backend of the event management system.
"""

import time
import types
import random
random.seed()
import logging
log = logging.getLogger("zen.Events")

from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Globals import DTMLFile
from Acquisition import aq_base
import DateTime
from Products.ZenModel.ZenossSecurity import *

from Products.ZenUtils.ObjectCache import ObjectCache


from ZEvent import ZEvent
from EventDetail import EventDetail
from BetterEventDetail import BetterEventDetail
from EventCommand import EventCommand
from Products.ZenEvents.Exceptions import *

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenUtils.FakeRequest import FakeRequest
from Products.ZenEvents.ZenEventClasses import Status_Ping, Status_Wmi_Conn

from ZenEventClasses import Unknown

from DbAccessBase import DbAccessBase

from Products.ZenUtils.Utils import unused

__pychecker__="maxargs=16"

def evtprep(evts):
    """
    Prepares data from L{Products.ZenEvents.EventManagerBase.getEventSummary}
    for rendering in the eventrainbow template macro.

    Each cell of the old-style event rainbow needs a CSS class specified in
    order to render its color, fill and border style.  evtprep determines the
    proper class and returns it, along with a string representation of the
    number of live and acknowledged events.

        >>> from Products.ZenEvents.EventManagerBase import evtprep
        >>> evtprep(['zenevents_5_noack noack', 2, 2])
        {'cssclass': 'zenevents_5_noack noack empty thin', 'data': '2/2'}
        >>> evtprep(['zenevents_5_noack noack', 1, 2])
        {'cssclass': 'zenevents_5_noack noack', 'data': '1/2'}

    @param evts: A tuple of the form (Severity string, Number Acknowledged int,
        Number Live int)
    @type evts: tuple
    @return: A dictionary of the form {'cssclass': Class string, 'data': Event
        count representation string}

    """
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
    ComponentWhere = ("\"(device = '%s' and component = '%s')\""
                      " % (me.device().getDmdKey(), me.getDmdKey())")
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
    historyMaxAgeDays = 0
    
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
        {'id':'historyMaxAgeDays', 'type':'int', 'mode':'w'},
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
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
          },
        )

    security = ClassSecurityInfo()
    

    def __init__(self, id, title='', hostname='localhost', username='root',
                 password='', database='events', port=3306,
                 defaultWhere='',defaultOrderby='',defaultResultFields=[]):
        """
        Sets up event database access and initializes the cache.

        @param id: A unique id
        @type id: string
        @param title: A title
        @type title: string
        @param hostname: The hostname of the events database server
        @type hostname: string
        @param username: The name of a user with permissions to access the
            events database
        @type username: string
        @param password: The password of the user
        @type password: string
        @param database: The name of the events database
        @type database: string
        @param port: The port on which the database server is listening
        @type port: int
        @param defaultWhere: The default where clause to use when building
            queries
        @type defaultWhere: string
        @param defaultOrderby: The default order by clause to use when building
            queries
        @type defaultOrderby: string
        @param defaultResultFields: DEPRECATED. Currently unused.
        @type defaultResultFields: list

        """
        unused(defaultOrderby, defaultResultFields)
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


    def getEventResultFields(self, context):
        """
        A wrapper for L{lookupManagedEntityResultFields} accepting an object
        with an C{event_key} attribute.

        >>> class dummy(object):
        ...     event_key = 'Device'
        ...
        >>> d = dummy()
        >>> f = dmd.ZenEventManager.getEventResultFields(d)
        >>> f==dmd.ZenEventManager.DeviceResultFields
        True
        >>> d.event_key = 'Robot'
        >>> f = dmd.ZenEventManager.getEventResultFields(d)
        >>> f==dmd.ZenEventManager.defaultResultFields
        True

        @param context: An object with an C{event_key} attribute.
        @type context: L{ManagedEntity}
        @return: A sequence of strings representing columns in the database.
        @rtype: tuple
        """
        return self.lookupManagedEntityResultFields(getattr(context,
                                                    'event_key', 'Default'))

    def getEventListME(self, me, **kwargs):
        """
        Queries the database for events on a managed entity.

        @param me: The object for which to fetch events
        @type me: L{ManagedEntity}
        @return: L{ZEvent} objects
        @rtype: list
        """
        where = ""
        if hasattr(me, 'getWhere'):
            where = me.getWhere()
        else:
            where = self.lookupManagedEntityWhere(me)
        try:
            resultFields = kwargs['resultFields']; del kwargs['resultFields']
        except KeyError: 
            resultFields = self.lookupManagedEntityResultFields(me.event_key)
        return self.getEventList(resultFields=resultFields, where=where,
                                 **kwargs)


    def getEventBatchME(self, me, selectstatus=None, resultFields=[], 
                        where="", orderby="", severity=None, state=2,
                        startdate=None, enddate=None, offset=0, rows=0,
                        getTotalCount=False, filter="", goodevids=[],
                        badevids=[], **kwargs):
        """
        Returns a batch of events based on criteria from checked rows on the
        event console.

        The event console can show thousands of events, and we want to support a
        "Select All" feature; enter this method. It builds a query based on the
        select status from the console ("All", "None", "Acknowledged",
        "Unacknowledged") and any checkboxes that have been modified manually.

        @param me: The managed entity for which to query events.
        @type me: L{ManagedEntity}
        @param resultFields: The columns to return from the database.
        @type resultFields: list
        @param where: The base where clause to modify.
        @type where: string
        @param orderby: The "ORDER BY" string governing sort order.
        @type orderby: string
        @param severity: The minimum severity for which to query.
        @type severity: int
        @param state: The minimum state for which to query.
        @type state: int
        @param startdate: The early date limit
        @type startdate: string, DateTime
        @param enddate: The late date limit
        @type enddate: string, DateTime
        @param offset: The row at which to begin returning
        @type offset: int
        @param rows: DEPRECATED The number of rows to return (ignored).
        @type rows: int
        @param getTotalCount: Whether or not to return a count of the total
            number of rows
        @type getTotalCount: bool
        @param filter: A glob by which to filter events
        @type filter: string
        @param goodevids: Ids of events that specifically should be included
        @type goodevids: list
        @param badevids: Ids of events that specifically should not be included
        @type badevids: list
        @return: Ids of matching events
        @rtype: list
        @todo: Remove unused parameters from the method definition
        """
        unused(getTotalCount, rows)
        newwhere = self.lookupManagedEntityWhere(me)
        if where: newwhere = self._wand(newwhere, '%s%s', where, '')
        where = newwhere
        badevidsstr, goodevidsstr = '',''
        if not isinstance(goodevids, (list, tuple)): goodevids = [goodevids]
        if not isinstance(badevids, (list, tuple)): badevids = [badevids]
        if badevids: badevidsstr = " and evid not in ('%s')" %(
                                            "','".join(badevids))
        if goodevids: goodevidsstr = " and evid in ('%s')" %(
                                            "','".join(goodevids))
        if selectstatus=='all':
            where += badevidsstr
        elif selectstatus=='none':
            where += goodevidsstr or ' and 0'
        elif selectstatus=='acked':
            oper = bool(goodevidsstr) and ' or' or ' and'
            where += goodevidsstr + oper + " (eventstate=1 %s) " % badevidsstr
        elif selectstatus=='unacked':
            oper = bool(goodevidsstr) and ' or' or 'and'
            where += goodevidsstr + oper + " (eventstate=0 %s) " % badevidsstr
        try:
            resultFields = kwargs['resultFields']; del kwargs['resultFields']
        except KeyError: 
            resultFields = self.lookupManagedEntityResultFields(me.event_key)
        events = self.getEventList(
                                    filter=filter,
                                    offset=offset,
                                    getTotalCount=False,
                                    startdate=startdate, 
                                    enddate=enddate, severity=severity,
                                    state=state, orderby=orderby,
                                    resultFields=resultFields,
                                    where=where,**kwargs)
        return [ev.evid for ev in events]


    def getEventList(self, resultFields=None, where="", orderby="",
            severity=None, state=2, startdate=None, enddate=None, offset=0,
            rows=0, getTotalCount=False, filter="", **kwargs):
        """
        Fetch a list of events from the database matching certain criteria.

        @param resultFields: The columns to return from the database.
        @type resultFields: list
        @param where: The base where clause to modify.
        @type where: string
        @param orderby: The "ORDER BY" string governing sort order.
        @type orderby: string
        @param severity: The minimum severity for which to query.
        @type severity: int
        @param state: The minimum state for which to query.
        @type state: int
        @param startdate: The early date limit
        @type startdate: string, DateTime
        @param enddate: The late date limit
        @type enddate: string, DateTime
        @param offset: The row at which to begin returning
        @type offset: int
        @param rows: The number of rows to return.
        @type rows: int
        @param getTotalCount: Whether or not to return a count of the total
            number of rows
        @type getTotalCount: bool
        @param filter: A glob by which to filter events
        @type filter: string
        @return: Matching events as L{ZEvent}s.
        @rtype: list
        @todo: Remove unused parameters from the method definition
        """
        unused(kwargs)
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
                select.append("limit %s, %s" % (offset, rows))
            select.append(';')
            select = " ".join(select)
            if getTotalCount: 
                try: retdata, totalCount = self.checkCache(select)
                except TypeError: 
                    retdata, totalCount = self.checkCache(select), 100
            else: retdata = self.checkCache(select)
            if not False:
                conn = self.connect()
                try:
                    curs = conn.cursor()
                    curs.execute(select)
                    retdata = []
                    # iterate through the data results and convert to python
                    # objects
                    if self.checkRemotePerm(ZEN_VIEW, self.dmd.Events):
                        eventPermission = True
                    else:
                        eventPermission = False
                    for row in curs.fetchall():
                        row = map(self.convert, resultFields, row)
                        evt = ZEvent(self, resultFields, row, eventPermission)
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
        Return the CSS class, number of acknowledged events, and number of
        unacknowledged events, per severity, for a C{ManagedEntity}.

        @param me: The object of the inquiry.
        @type me: L{ManagedEntity}
        @param severity: The minimum severity for which to retrieve events
        @type severity: int
        @param state: The minimum state for which to retrieve events
        @type state: int
        @param prodState: The minimum production state for which to retrieve
            events
        @type prodState: int
        @return: List of lists of the form [class, acked count, unacked count].
        @rtype: list
        """ 
        try:
            where = self.lookupManagedEntityWhere(me)
            return self.getEventSummary(where, severity, state, prodState)
        except:
            log.exception("event summary for %s failed" % me.getDmdKey())
            raise


    def getEventSummary(self, where="", severity=1, state=1, prodState=None):
        """
        Return a list of tuples with number of events and the color of the
        severity that the number represents.

        This method should not be called directly, but overridden by subclasses.

        @param where: The base where clause to modify.
        @type where: string
        @param severity: The minimum severity for which to retrieve events
        @type severity: int
        @param state: The minimum state for which to retrieve events
        @type state: int
        @param prodState: The minimum production state for which to retrieve
            events
        @type prodState: int
        @return: List of lists of the form [class, acked count, unacked count].
        @rtype: list
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
        """
        Return an EventDetail object for a particular event.

        @param evid: Event ID
        @type evid: string
        @param dedupid: string used to determine duplicates
        @type dedupid: string
        @param better: provide even more detail than normal?
        @type better: boolean
        @return: fields from the event
        @rtype: EventDetail object
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
        conn = self.connect()
        try:
            curs = conn.cursor()
            curs.execute(selectevent)
            evrow = curs.fetchone()
            if not evrow:
                raise ZenEventNotFound( "Event id '%s' not found" % evid)
            evdata = map(self.convert, fields, evrow)
            if better:
                event = BetterEventDetail(self, fields, evdata)
            else:
                event = EventDetail(self, fields, evdata)

            selectdetail = "select name, value from %s where" % self.detailTable
            selectdetail += " evid = '%s'" % event.evid
            #print selectdetail
            curs.execute(selectdetail)
            event._details = curs.fetchall()

            selectlogs = "select userName, ctime, text"
            selectlogs += " from %s where" % self.logTable
            selectlogs += " evid = '%s' order by ctime desc" % event.evid
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
        from Products.ZenModel.Organizer import Organizer
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
        for name in "device", "component", "eventClass", "systems":
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
                    statusCache.append([alink, comp, dtime, devname])
                if limit:
                    statusCache = statusCache[:limit]
                cleanup()
            finally: self.close(conn)
        return statusCache


    def getHeartbeatObjects(self, failures=True, simple=False, limit=0, db=None):
        beats = self.getHeartbeat(failures, simple, limit, db)
        return [{'alink':b[0], 'comp':b[1], 'dtime':b[2], 'devId':b[3]}
                for b in beats]

        
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
                result[dev,comp] = count
            return result 
        finally:
            self.close(conn)


    def getMaxSeverity(self, me):
        """ Returns the severity of the most severe event. """
        where = self.lookupManagedEntityWhere(me.device())
        if me.event_key == 'Component':
            where = self._wand(where, "%s = '%s'",
                self.componentField, me.id)
        select = "select max(%s) from %s where " % (self.severityField, 
            self.statusTable)
        query = select + where
        conn = self.connect()
        try:
            curs = conn.cursor()
            curs.execute(query)
            severity = curs.fetchall()[0][0]
        finally: self.close(conn)
        return max(severity, 0)


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

    def getBatchComponentInfo(self, components):
        """
        Given a list of dicts with keys 'device', 'component', make a query to
        get an overall severity and device status for the group.
        """
        severity, state = 3, 1
        components = list(components) # Sometimes a generator. We use it twice.

        def doQuery(query):
            conn = self.connect()
            data = None
            try:
                curs = conn.cursor()
                curs.execute(query)
                data = curs.fetchall()
            finally: self.close(conn)
            return data

        select = "select MAX(%s) from %s where " % (self.severityField, 
                                                    self.statusTable)
        where = self._wand("", "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        def componentWhere(device, component):
            return "device = '%s' and component= '%s'" % (device, component)
        cwheres = ' and ' + ' or '.join(['(%s)'% componentWhere(**comp) 
                                        for comp in components])
        sevquery = select + where + cwheres

        select = "select MAX(%s) from %s where " % (self.countField, 
                                                    self.statusTable)
        where = self._wand("", "%s >= %s", self.severityField, severity)
        where = self._wand(where, "%s <= %s", self.stateField, state)
        where = self._wand(where, "%s = '%s'", self.eventClassField,
                           '/Status/Ping')
        devwhere = lambda d:"device = '%s'" % d
        dwheres = ' and ' + '(%s)' % (' or '.join(
            map(devwhere, [x['device'] for x in components])))
        statquery = select + where + dwheres

        maxseverity = doQuery(sevquery)[0][0]
        maxstatus = doQuery(statquery)[0][0]
        return maxseverity, maxstatus

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
        """
        Lookup and build where clause for managed entity.

        @param me: managed entity
        @type me: object
        @return: where clause
        @rtype: string
        """
        key = me.event_key + "Where"
        wheretmpl = getattr(aq_base(self), key, False)
        if not wheretmpl:
            raise ValueError("No 'where' clause found for event_key %s" % me.event_key)
        return eval(wheretmpl,{'me':me})


    def lookupManagedEntityField(self, event_key):
        """
        Lookup database field for managed entity default 
        using event_key.

        @param event_key: event
        @type event_key: string
        @return: field for the managed entity
        @rtype: object
        """
        key = event_key + "Field"
        return getattr(aq_base(self), key, event_key)


    def lookupManagedEntityResultFields(self, event_key):
        """
        Gets the column names that should be requested in an event query for
        this entity type.

        Returns a set of result fields predefined for this entity type.  If
        none have been defined, returns the default result fields.

        >>> f = dmd.ZenEventManager.lookupManagedEntityResultFields('Device')
        >>> f==dmd.ZenEventManager.DeviceResultFields
        True
        >>> f = dmd.ZenEventManager.lookupManagedEntityResultFields('Robot')
        >>> f==dmd.ZenEventManager.defaultResultFields
        True

        @param event_key: The event key of a managed entity.
        @type event_key: string
        @return: A tuple of strings representing columns in the database.
        """
        key = event_key + "ResultFields"
        return getattr(aq_base(self), key, self.defaultResultFields)


    def _wand(self, where, fmt, field, value):
        """
        >>> dmd.ZenEventManager._wand('where 1=1', '%s=%s', 'a', 'b')
        'where 1=1 and a=b'
        >>> dmd.ZenEventManager._wand('where a=5', '%s=%s', 'a', 'b')
        'where a=5'
        >>> dmd.ZenEventManager._wand('where b=a', '%s=%s', 'a', 'b')
        'where b=a'
        """
        if value != None and where.find(field) == -1:
            if where: where += " and "
            where += fmt % (field, value)
        return where

    def _setupDateRange(self, startdate=None,
                              enddate=None):
        """
        Make a start and end date range that is at least one day long.
        returns a start and end date as a proper database element.
        """
        if enddate is None:
            enddate = DateTime.DateTime()-1
        if startdate is None:
            startdate = DateTime.DateTime()
        if type(enddate) == types.StringType:
            enddate = DateTime.DateTime(enddate, datefmt='us')
        enddate = enddate.latestTime()
        if type(startdate) == types.StringType:
            startdate = DateTime.DateTime(startdate, datefmt='us')
        startdate = startdate.earliestTime()
        startdate = self.dateDB(startdate)
        enddate = self.dateDB(enddate)
        return startdate, enddate

    def getAvgFieldLength(self, fieldname):
        conn = self.connect()
        try:
            curs = conn.cursor()
            selstatement = ("SELECT AVG(CHAR_LENGTH(mycol))+20 FROM (SELECT %s AS "
                            "mycol FROM %s WHERE %s IS NOT NULL LIMIT 500) AS "
                            "a;") % (fieldname, self.statusTable, fieldname)
            curs.execute(selstatement)
            avglen = curs.fetchone()
        finally: self.close(conn)
        try: return float(avglen[0])
        except TypeError: return 10. 


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
        """
        Send an event to the backend.

        @param event: event
        @type event: event object
        @todo: implement
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

    security.declareProtected(ZEN_COMMON,'getSeverities')
    def getSeverities(self):
        """Return a list of tuples of severities [('Warning', 3), ...] 
        """
        return self.severityConversions

    def getSeverityString(self, severity):
        """Return a string representation of the severity.
        """
        try:
            return self.severities[severity]
        except KeyError:
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

            
    def convertEventField(self, field, value, default=""):
        """
        Convert numeric values commonly found in events to their textual
        representation.
        """
        if value is None: return default
        try:
            value = int(value)
        except ValueError:
            return "unknown (%r)" % (value,)

        if field == 'severity' and self.severities.has_key(value):
            return "%s (%d)" % (self.severities[value], value)
        elif field == "priority" and self.priorities.has_key(value):
            return "%s (%d)" % (self.priorities[value], value)
        elif field == 'eventState':
            if value < len(self.eventStateConversions):
                return "%s (%d)" % (self.eventStateConversions[value][0], value)
        elif field == "prodState":
            prodState = self.dmd.convertProdState(value)
            if isinstance(prodState, types.StringType):
                return "%s (%d)" % (prodState, value)
        elif field == "DevicePriority":
            priority = self.dmd.convertPriority(value)
            if isinstance(priority, types.StringType):
                return "%s (%d)" % (priority, value)

        return "unknown (%r)" % (value,)


    def getStatusCssClass(self, status):
        if status < 0: status = "unknown"
        elif status > 3: status = 3
        return "zenstatus_%s" % status


    def getStatusImgSrc(self, status):
        ''' Return the img source for a status number
        '''
        if status < 0:
            src = 'grey'
        elif status == 0:
            src = 'green'
        else:
            src = 'red'
        return '/zport/dmd/img/%s_dot.png' % src


    def getEventCssClass(self, severity, acked=False):
        """return the css class name to be used for this event.
        """
        __pychecker__='no-constCond'
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
        """
        Prepare string values for db by escaping special characters.

        @param value: string
        @type value: string
        @todo: implement
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
                if self.backend == "mysql":
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
            summary = REQUEST.get('summary', ''),
            message = REQUEST.get('message', ''),
            device = REQUEST.get('device', ''),
            component = REQUEST.get('component', ''),
            severity = REQUEST.get('severity', ''),
            eventClassKey = REQUEST.get('eventClassKey', ''),
            )
        # We don't want to put empty eventClass into the dict because that
        # can keep the event from being mapped to /Unknown correctly.
        if REQUEST.get('eclass', None):
            eventDict['eventClass'] = REQUEST['eclass']
        # sendEvent insists on a device or a component. Can be bogus.
        if not eventDict['device'] and not eventDict['component']:
            if REQUEST:
                REQUEST['message'] = 'You must specify a device and/or a component.'
                return self.callZenScreen(REQUEST)
            else:
                return
        self.sendEvent(eventDict)            
        if REQUEST:
            REQUEST['RESPONSE'].redirect('/zport/dmd/Events/viewEvents')


    def deleteEvents(self, whereClause, reason):
        self.updateEvents('DELETE FROM status', whereClause, reason)


    security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        "Delete the given event ids"
        if type(evids) == type(''):
            evids = [evids]
        num = len(evids)
        if evids:
            evids = ",".join([ "'%s'" % evid for evid in evids])
            whereClause = ' where evid in (%s)' % evids
            self.deleteEvents(whereClause, 'Deleted by user')
        if REQUEST:
            REQUEST['message'] = 'Moved %s event%s to History.' % (
                                    num, (num != 1 and 's') or '')
            return self.callZenScreen(REQUEST)

    def undeleteEvents(self, whereClause, reason):
        fields = ','.join( self.getFieldList() )
        # We want to blank clearid
        fields = fields.replace('clearid','NULL')
        self.updateEvents(  'INSERT status ' + \
                            'SELECT %s FROM history' % fields,
                            whereClause + \
                            ' ON DUPLICATE KEY UPDATE status.count=status.count+history.count', 
                            reason, 'history', toLog=False)
        self.updateEvents( 'DELETE FROM history', whereClause, \
                            reason, 'history')

    security.declareProtected('Manage Events','manage_undeleteEvents')
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        "Move the given event ids into status and delete from history"
        if type(evids) == type(''):
            evids = [evids]
        num = len(evids)
        if evids:
            evids = ",".join([ "'%s'" % evid for evid in evids])
            whereClause = ' where evid in (%s)' % evids
            self.undeleteEvents(whereClause, 'Undeleted by user')
        if REQUEST: 
            REQUEST['message'] = "%s events undeleted." % num
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteAllEvents')
    def manage_deleteAllEvents(self, devname, REQUEST=None):
        "Delete the events for a given Device (used for deleting the device"
        whereClause = 'where device = "%s"' % devname
        self.deleteEvents(whereClause, 'Device deleted')
        if REQUEST:
            REQUEST['message'] = 'Deleted all events for %s' % devname
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHistoricalEvents')
    def manage_deleteHistoricalEvents(self, devname=None, agedDays=None,
                                        REQUEST=None):
        """
        Delete historical events.  If devices is given then only delete
        events for that device.  If agedDays is given then only delete
        events that are older than that many days.
        devname and agedDays are mutually exclusive.  No real reason for this
        other than there is no current need to use both in same call and I
        don't want to test the combination.
        This is an option during device deletion.  It is also used
        by zenactions to keep history table clean.
        
        NB: Device.deleteDevice() is not currently calling this when devices
        are deleted.  See ticket #2996.
        """
        import subprocess
        import os
        import Products.ZenUtils.Utils as Utils

        cmd = Utils.zenPath('Products', 'ZenUtils', 'ZenDeleteHistory.py')
        if devname:
            args = ['--device=%s' % devname]
        elif agedDays:
            args = ['--numDays=%s' % agedDays]
        else:
            return
        proc = subprocess.Popen(
                [cmd]+args, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, env=os.environ)
        # We are abandoning this proc to do it's thing. or not.  We don't
        # want to block because we would delay user feedback on a device
        # delete when this might take a while to perform.
        unused(proc)
        if REQUEST:
            REQUEST['message'] = 'Deleted historical events'
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, devname, REQUEST=None):
        if devname:
            delete = "delete from heartbeat where device = '%s'" % devname
            conn = self.connect()
            try:
                curs = conn.cursor()
                curs.execute(delete);
            finally: self.close(conn)
        if REQUEST:
            REQUEST['message'] = 'Moved heartbeat(s) to History'
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    def manage_ackEvents(self, evids=(), REQUEST=None):
        "Ack the given event ids"
        if type(evids) == type(''):
            evids = [evids]
        request = FakeRequest()
        self.manage_setEventStates(1 , evids, REQUEST=request)
        if REQUEST:
            dest = '/zport/dmd/Events/viewEvents'
            if request.get('message', ''):
                dest += '?message=%s' % request['message']
            if not getattr(REQUEST, 'dontRedirect', False):
                REQUEST['RESPONSE'].redirect(dest)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_setEventStates(self, eventState=None, evids=(), 
                              userid="", REQUEST=None):
        reason = None
        if eventState and evids:
            eventState = int(eventState)
            if eventState > 0 and not userid: 
                userid = getSecurityManager().getUser()
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
        if REQUEST:
            if reason:
                REQUEST['message'] = reason
            else:
                REQUEST['message'] = 'no reason'
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_createEventMap(self, eventClass=None, evids=(),
                              REQUEST=None):
        """Create an event map from an event or list of events.
        """
        evclass = None
        evmap = None
        numCreated = 0
        numNotUnknown = 0
        numNoKey = 0
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
                    if curevclass != Unknown:
                        numNotUnknown += 1
                        continue                        
                    if not evclasskey:
                        numNoKey += 1
                        continue
                    evmap = evclass.createInstance(evclasskey)
                    evmap.eventClassKey = evclasskey
                    evmap.example = msg
                    numCreated += 1
                    evmap.index_object()
            finally: self.close(conn)
        elif REQUEST:
            if not evids:
                REQUEST['message'] = 'No events selected.'
            elif not eventClass:
                REQUEST['message'] = 'No event class selected.'
                
        if REQUEST:
            msg = REQUEST.get('message', '')
            if numNotUnknown:
                msg += ((msg and ' ') + 
                        '%s event%s %s not class /Unknown.' % (
                            numNotUnknown, 
                            (numNotUnknown != 1 and 's') or '',
                            (numNotUnknown != 1 and 'are') or 'is'))
            if numNoKey:
                msg += ((msg and ' ') +
                        '%s event%s %s not have an event class key.' % (
                            numNoKey,
                            (numNoKey != 1 and 's') or '',
                            (numNoKey != 1 and 'do') or 'does'))
            msg += (msg and ' ') + 'Created %s event mapping%s.' % (
                            numCreated,
                            (numCreated != 1 and 's') or '')
            REQUEST['message'] = msg
            # EventView might pass a fake Request during an ajax call from
            # event console.  Don't bother rendering anything in this case.
            if getattr(REQUEST, 'dontRender', False):
                return ''
            if len(evids) == 1 and evmap:
                REQUEST['RESPONSE'].redirect(evmap.absolute_url())
            elif evclass and evmap:
                REQUEST['RESPONSE'].redirect(evclass.absolute_url())


    security.declareProtected('Manage EventManager','manage_refreshConversions')
    def manage_refreshConversions(self, REQUEST=None):
        """get the conversion information from the database server"""
        assert(self == self.dmd.ZenEventManager)
        self.loadSchema()
        self.dmd.ZenEventHistory.loadSchema()
        if REQUEST:
            REQUEST['message'] = 'Event schema refreshed' 
            return self.callZenScreen(REQUEST)


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
        if REQUEST: 
            REQUEST['message'] = 'Event cache cleared'
            return self.callZenScreen(REQUEST)


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
        if REQUEST: 
            REQUEST['message'] = 'Heartbeats cleared'
            return self.callZenScreen(REQUEST)

    security.declareProtected('Manage EventManager','zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        ''' Need to handle editing of history event fields differently
        '''
        assert(self == self.dmd.ZenEventManager)
        screenName = REQUEST.get('zenScreenName', '')
        if screenName == 'editEventManagerHistoryFields':
            obj = self.dmd.ZenEventHistory
        else:
            obj = self
        if screenName == 'editEventManager':
            # We renamed the password field to try to keep browsers from
            # asking user if they wanted to save the password.
            if REQUEST.has_key('mysql_pass'):
                REQUEST.form['password'] = REQUEST['mysql_pass']
        editProperties = ZenModelRM.zmanage_editProperties
        # suppress 'self is not first method argument' from pychecker
        editProperties(obj, REQUEST)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage Events', 'manage_addLogMessage')
    def manage_addLogMessage(self, evid=None, message='', REQUEST=None):
        """
        Add a log message to an event
        """
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
        self.dmd.ZenEventHistory.clearCache('evid' + evid)
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
            self.commands._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


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
