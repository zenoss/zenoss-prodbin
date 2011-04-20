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
import logging
log = logging.getLogger("zen.EventView")

from _mysql_exceptions import MySQLError

from AccessControl import ClassSecurityInfo, getSecurityManager
from Globals import InitializeClass
from zope.interface import Interface, implements

from Products.ZenUtils.FakeRequest import FakeRequest
from Products.ZenUtils.Utils import unused
from Products.Zuul import getFacade
from Products.Zuul.decorators import deprecated
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenWidgets import messaging
from zenoss.protocols.services import ServiceResponseError
from zenoss.protocols.services.zep import ZepConnectionError
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED, \
    SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING

class IEventView(Interface):
    """
    Marker interface for objects which have event views.
    """

def zepConnectionError(retval=None):
    def outer(func):
        def inner(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ZepConnectionError, e:
                msg = 'Connection refused. Check zenoss-zep status on <a href="/zport/About/zenossInfo">Daemons</a>'
                messaging.IMessageSender(self).sendToBrowser("ZEP connection error",
                                                        msg,
                                                        priority=messaging.CRITICAL,
                                                        sticky=True)
                log.warn("Could not connect to ZEP")
            return retval
        return inner
    return outer

class EventView(object):
    """
    This class provides convenience methods for retrieving events to any subclass. Note that
    this class is currently transitioning between the old event system and ZEP. Most of the methods
    are marked as deprecated except those that go through ZEP.

    """
    implements(IEventView)

    security = ClassSecurityInfo()

    @deprecated
    def getEventManager(self, table='status'):
        """Return the current event manager for this object.
        """
        if table=='history':
            return self.ZenEventHistory
        return self.ZenEventManager

    @deprecated
    def getEventHistory(self):
        """Return the current event history for this object.
        """
        return self.ZenEventHistory

    def getStatusString(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        # used to avoid pychecker complaint about wrong # of args to getStatus
        f = self.getStatus
        return self.convertStatus(f(statclass, **kwargs))

    @deprecated
    def getEventSummary(self, severity=1, state=1, prodState=None):
        """Return an event summary list for this managed entity.
        """
        return self.getEventManager().getEventSummaryME(self, severity, state, prodState)

    def getEventOwnerList(self, severity=0, state=1):
        """Return list of event owners for this mangaed entity.
        """
        return self.getEventManager().getEventOwnerListME(self, severity, state)

    def getStatusImgSrc(self, status):
        ''' Return the image source for a status number
        '''
        return self.getEventManager().getStatusImgSrc(status)

    def getStatusCssClass(self, status):
        """Return the css class for a status number.
        """
        return self.getEventManager().getStatusCssClass(status)

    @deprecated
    def getEventDetail(self, evid=None, dedupid=None, better=False):
        """
        Return an EventDetail for an event on this object.
        """
        evt = self.getEventManager().getEventDetail(evid, dedupid, better)
        return evt.__of__(self)

    @deprecated
    def getEventDetailFromStatusOrHistory(self, evid=None,
                                            dedupid=None, better=False):
        """
        Return the event detail for an event within the context of a device
        or other device organizer
        """
        evt = self.getEventManager().getEventDetailFromStatusOrHistory(
                                        evid, dedupid, better)
        return evt.__of__(self)

    @deprecated
    def convertEventField(self, field, value, default=""):
        return self.getEventManager().convertEventField(field, value, default)


    security.declareProtected('Manage Events','manage_addLogMessage')
    @deprecated
    def manage_addLogMessage(self, evid=None, message='', REQUEST=None):
        """
        Add a log message to an event
        """
        self.getEventManager().manage_addLogMessage(evid, message)
        if REQUEST: return self.callZenScreen(REQUEST)

    security.declareProtected('Manage Events','manage_deleteBatchEvents')
    @deprecated
    def manage_deleteBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        """
        unused(count)
        evids = self.getEventManager().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_deleteEvents(evids, request)
        return request.get('message', '')



    #security.declareProtected('Manage Events','manage_undeleteBatchEvents')
    @deprecated
    def manage_undeleteBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        Only called from event console, so uses FakeRequest to avoid
        page rendering.
        """
        unused(count)
        evids = self.getEventHistory().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_undeleteEvents(evids, request)
        return request.get('message', '')


    security.declareProtected('Manage Events','manage_ackBatchEvents')
    @deprecated
    def manage_ackBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='',
                                    offset=0, count=50, fields=[],
                                    getTotalCount=True,
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        Only called from event console, so uses FakeRequest to avoid
        page rendering.
        """
        unused(count)
        evids = self.getEventManager().getEventBatchME(self,
                                            selectstatus=selectstatus,
                                            goodevids=goodevids,
                                            badevids=badevids,
                                            filter=filter,
                                            offset=offset, fields=fields,
                                            getTotalCount=getTotalCount,
                                            startdate=startdate,
                                            enddate=enddate, severity=severity,
                                            state=state, orderby=orderby,
                                            **kwargs)
        request = FakeRequest()
        self.manage_ackEvents(evids, request)
        return request.get('message', '')


    security.declareProtected('Manage Events','manage_setEventStates')
    @deprecated
    def manage_setEventStates(self, eventState=None, evids=(),
                              userid="", REQUEST=None):
        """Set event state form this managed entity.
        """
        return self.getEventManager().manage_setEventStates(
            eventState, evids, userid, REQUEST)


    security.declareProtected('Manage Events','manage_createEventMap')
    @deprecated
    def manage_createEventMap(self, eventClass=None, evids=(),
                              table='status', REQUEST=None):
        """Create an event map from an event or list of events.
        """
        screen = self.getEventManager(table).manage_createEventMap(
                                      eventClass, evids, REQUEST)
        if REQUEST:
            if screen: return screen
            return self.callZenScreen(REQUEST)

    def _getCurrentUserName(self):
        return getSecurityManager().getUser().getId()

    def _redirectToEventConsole(self, msg, REQUEST=None):
        messaging.IMessageSender(self).sendToBrowser("Events",
                                                     msg,
                                                     priority=messaging.INFO)
        if REQUEST:
            dest = '/zport/dmd/Events/evconsole'
            REQUEST['RESPONSE'].redirect(dest)

    security.declareProtected('Manage Events','manage_ackEvents')
    @zepConnectionError
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state from this managed entity.
        """
        zep = getFacade('zep')
        if isinstance(evids, basestring):
            evids = [evids]

        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.acknowledgeEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Acknowledged events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError, e:
            self._redirectToEventConsole("Error acknowledging events: %s" % str(e), REQUEST)

    security.declareProtected('Manage Events','manage_deleteEvents')
    @zepConnectionError
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events from this managed entity.
        """
        zep = getFacade('zep')
        if isinstance(evids, basestring):
            evids = [evids]
        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.closeEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Closed events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError, e:
            self._redirectToEventConsole("Error Closing events: %s" % str(e), REQUEST)

    security.declareProtected('Manage Events','manage_undeleteEvents')
    @zepConnectionError
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events from this managed entity.
        """
        zep = getFacade('zep')
        if isinstance(evids, basestring):
            evids = [evids]
        try:
            evids_filter = zep.createEventFilter(uuid=evids)
            zep.reopenEventSummaries(eventFilter=evids_filter)
            self._redirectToEventConsole("Reopened events: %s" % ", ".join(evids), REQUEST)
        except ServiceResponseError, e:
            self._redirectToEventConsole("Error Reopening events: %s" % str(e), REQUEST)

    @zepConnectionError(0)
    def getStatus(self, statusclass=None, **kwargs):
        """
        Return the status number for this device of class statClass.
        """
        zep = getFacade('zep')
        try:
            event_filter = zep.createEventFilter(tags=[self.getUUID()],
                                                 severity=[SEVERITY_WARNING,SEVERITY_ERROR,SEVERITY_CRITICAL],
                                                 status=[STATUS_NEW,STATUS_ACKNOWLEDGED],
                                                 event_class=filter(None, [statusclass]))
        except TypeError, e:
            log.warn("Attempted to query events for %r which does not have a uuid" % self)
            return 0
        result = zep.getEventSummaries(0, filter=event_filter, limit=0)
        return int(result['total'])

    def getUUID(self):
        return IGlobalIdentifier(self).getGUID()

    @zepConnectionError({})
    def getEventSeveritiesCount(self):
        """
        Uses the zep facade to return a list of
        event summaries for this entity
        """
        zep = getFacade('zep')
        try:
            severities = zep.getEventSeveritiesByUuid(self.getUUID())
        except TypeError, e:
            log.warn("Attempted to query events for %r which does not have a uuid" % self)
            return {}
        results = dict((zep.getSeverityName(sev).lower(), count) for (sev, count) in severities.iteritems())
        return results

    @zepConnectionError(0)
    def getWorstEventSeverity(self):
        """
        Uses Zep to return the worst severity for this object
        """
        zep = getFacade('zep')
        try:
            result =  zep.getWorstSeverityByUuid(self.getUUID())
        except TypeError, e:
            log.warn("Attempted to query events for %r which does not have a uuid" % self)
            result = 0
        return result

InitializeClass(EventView)
