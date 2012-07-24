##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """EventManagerBase
Data connector to backend of the event management system.
"""

import time
import random
random.seed()
import logging
log = logging.getLogger("zen.Events")

from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils import Time
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

from Products.ZenUtils.Utils import unused
from .HeartbeatUtils import getHeartbeatObjects

__pychecker__="maxargs=16"

class EventManagerBase(ZenModelRM):
    """
    Data connector to backend of the event management system.
    """

    eventStateConversions = (
                ('New',         0),
                ('Acknowledged',1),
                ('Suppressed',  2),
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
    DeviceResultFields = ("eventState", "severity", "component", "eventClass",
                          "summary", "firstTime", "lastTime", "count" )
    ComponentWhere = ("\"(device = '%s' and component = '%s')\""
                      " % (me.device().getDmdKey(), escape_string(me.name()))")
    ComponentResultFields = ("eventState", "severity", "eventClass", "summary",
                             "firstTime", "lastTime", "count" )
    IpAddressWhere = "\"ipAddress='%s'\" % (me.getId())"
    EventClassWhere = "\"eventClass like '%s%%'\" % me.getDmdKey()"
    EventClassInstWhere = """\"eventClass = '%s' and eventClassKey = '%s'\" % (\
                                me.getEventClass(), me.eventClassKey)"""
    DeviceClassWhere = "\"(DeviceClass = '%s' or DeviceClass like '%s/%%') \" % \
                         ( me.getDmdKey(), me.getDmdKey() )"

    LocationWhere = "\"Location like '%s%%'\" % me.getDmdKey()"
    SystemWhere = "\"Systems like '%%|%s%%'\" % me.getDmdKey()"
    DeviceGroupWhere = "\"DeviceGroups like '%%|%s%%'\" % me.getDmdKey()"

    defaultResultFields = ("eventState", "severity", "device", "component",
                           "eventClass", "summary", "firstTime", "lastTime",
                           "count" )

    defaultFields = ('eventState', 'severity', 'evid')

    defaultEventId = ('device', 'component', 'eventClass',
                         'eventKey', 'severity')

    requiredEventFields = ('device', 'summary', 'severity')

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

        self.defaultWhere = defaultWhere
        self.defaultOrderby="%s desc, %s desc" % (
                            self.severityField, self.lastTimeField)

    def restrictedUserFilter(self, where):
        """This is a hook do not delete me!"""
        return where

    def defaultAvailabilityStart(self):
        return Time.USDate(time.time() - 60*60*24*self.defaultAvailabilityDays)


    def defaultAvailabilityEnd(self):
        return Time.USDate(time.time())


    def getAvailability(self, state, **kw):
        import Availability
        allowedFilters = (
            "device", "component", "eventClass", "systems", "severity",
            "prodState", "manager", "agent", "DeviceClass", "Location",
            "System", "DeviceGroup", "DevicePriority", "monitor")

        for name in allowedFilters:
            if hasattr(state, name):
                kw.setdefault(name, getattr(state, name))
        if getattr(state, 'startDate', None) is not None:
            kw.setdefault('startDate', Time.ParseUSDate(state.startDate))
        if getattr(state, 'endDate', None) is not None:
            # End date needs to be inclusive of events that occurred on that
            # date. So we advance to the last second of the day.
            kw.setdefault('endDate', Time.getEndOfDay(Time.ParseUSDate(
                state.endDate)))
        kw.setdefault('startDate',
                      time.time() - 60*60*24*self.defaultAvailabilityDays)
        return Availability.query(self.dmd, **kw)

    def getHeartbeatObjects(self, failures=True, simple=False, limit=0,
            db=None):
        return getHeartbeatObjects(failures, limit,
                self.getDmdRoot("Devices") if not simple else None)

    def getMaxSeverity(self, me):
        from Products.Zuul.facades import getFacade
        """ Returns the severity of the most severe event. """
        zep = getFacade('zep')
        try:
            # Event class rainbows show all events through DEBUG severity
            uuid = IGlobalIdentifier(me).getGUID()
            return zep.getWorstSeverityByUuid(uuid)
        except TypeError, e:
            log.warn("Attempted to query events for %r which does not have a uuid" % self)
            return 0


    #==========================================================================
    # Event sending functions
    #==========================================================================

    security.declareProtected(ZEN_SEND_EVENTS, 'sendEvents')
    def sendEvents(self, events):
        """Send a group of events to the backend.
        """
        raise NotImplementedError


    security.declareProtected(ZEN_SEND_EVENTS, 'sendEvent')
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
