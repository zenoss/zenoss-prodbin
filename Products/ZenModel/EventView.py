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
            return self.getEventManager().getStatusME(self, 
                                        statusclass=statusclass, **kwargs)
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
        self.getEventManager().manage_deleteEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_undeleteEvents')
    def manage_undeleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        self.getEventManager().manage_undeleteEvents(evids)
        if REQUEST: 
            REQUEST['message'] = '%s events undeleted.' % len(evids)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, REQUEST=None):
        """Delete events form this managed entity.
        """
        dev = self.device()
        if dev: 
            self.getEventManager().manage_deleteHeartbeat(dev.id)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_ackEvents')
    def manage_ackEvents(self, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        self.getEventManager().manage_ackEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    security.declareProtected('Manage Events','manage_setEventStates')
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        self.getEventManager().manage_setEventStates(eventState, evids)
        if REQUEST: return self.callZenScreen(REQUEST)


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
