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

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

class FakeRequest(dict):
    ''' Used for ajax calls from event console and elsewhere.  This is used
    as a container for REQUEST['message'] which we are interested in.  It has
    the advantage over the regular REQUEST object in that it won't actually
    bother to render anything when callZenScreen() is called with one.
    '''
    dontRender = True
    
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self['oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'] = True
        
    def setMessage(self, R):
        if R and self.get('message', ''):
            R['message'] = self['message']


class EventView(object):

    security = ClassSecurityInfo()
   
    def getEventManager(self, table='status'):
        """Return the current event manager for this object.
        """
        if table=='history':
            return self.ZenEventHistory
        return self.ZenEventManager


    def getEventHistory(self):
        """Return the current event history for this object.
        """
        return self.ZenEventHistory


    def getJSONEventsInfo(self, offset=0, count=50, fields=[], 
                          getTotalCount=True, 
                          
                          filter='', severity=2, state=1, 
                          orderby='', REQUEST=None):
        """Return the current event list for this managed entity.
        """
        kwargs = locals(); del kwargs['self']
        return self.getEventManager().getJSONEventsInfo(self, **kwargs)


    def getJSONHistoryEventsInfo(self, offset=0, count=50, fields=[], 
                          getTotalCount=True, 
                          startdate=None, enddate=None,
                          filter='', severity=2, state=1, 
                          orderby='', REQUEST=None):
        """Return the current event list for this managed entity.
        """
        kwargs = locals(); del kwargs['self']
        return self.getEventHistory().getJSONEventsInfo(self, **kwargs)


    def getJSONFields(self, history=False):
        """Return the current event list for this managed entity.
        """
        if history: return self.getEventHistory().getJSONFields(self)
        else: return self.getEventManager().getJSONFields(self)


    def getStatus(self, statusclass=None, **kwargs):
        """Return the status number for this device of class statClass.
        """
        try:
            return self.getEventManager().getStatusME(self, statusclass=statusclass, **kwargs)
        except MySQLError: 
            log.exception("exception getting status")
            return -1


    def getStatusString(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        return self.convertStatus(self.getStatus(statclass, **kwargs))
                                                        
    
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

    
    security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        # If we pass REQUEST in to the getEventManager().manage_deleteEvents()
        # call we don't get a proper refresh of the event console.  It only
        # works if self.callZenScreen() is called from here rather than down
        # in the event manager.  I'm not sure why.  Using FakeResult to fetch
        # the message seems like best workaround for now.
        request = FakeRequest()
        self.getEventManager().manage_deleteEvents(evids, request)
        if REQUEST:
            request.setMessage(REQUEST)
            return self.callZenScreen(REQUEST)


    #security.declareProtected('Manage Events','manage_deleteBatchEvents')
    def manage_deleteBatchEvents(self, selectstatus='none', goodevids=[],
                                    badevids=[], filter='', 
                                    offset=0, count=50, fields=[], 
                                    getTotalCount=True, 
                                    startdate=None, enddate=None,
                                    severity=2, state=1, orderby='',
                                    REQUEST=None, **kwargs):
        """Delete events form this managed entity.
        """
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


    security.declareProtected('Manage Events','manage_undeleteEvents')
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        request = FakeRequest()
        self.getEventManager().manage_undeleteEvents(evids, request)
        if REQUEST:
            request.setMessage(REQUEST)
            return self.callZenScreen(REQUEST)


    #security.declareProtected('Manage Events','manage_undeleteBatchEvents')
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


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, REQUEST=None):
        """Delete events form this managed entity.
        """
        dev = self.device()
        if dev: 
            return self.getEventManager().manage_deleteHeartbeat(dev.id, REQUEST)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        return self.getEventManager().manage_ackEvents(evids, REQUEST)


    security.declareProtected('Manage Events','manage_ackBatchEvents')
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
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        return self.getEventManager().manage_setEventStates(
                                                eventState, evids, REQUEST)


    security.declareProtected('Manage Events','manage_createEventMap')
    def manage_createEventMap(self, eventClass=None, evids=(), 
                              table='status', REQUEST=None):
        """Create an event map from an event or list of events.
        """
        screen = self.getEventManager(table).manage_createEventMap(
                                      eventClass, evids, REQUEST)
        if REQUEST:
            if screen: return screen
            return self.callZenScreen(REQUEST)


InitializeClass(EventView)
