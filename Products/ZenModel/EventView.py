import logging
log = logging.getLogger("zen.EventView")

from _mysql_exceptions import MySQLError


class EventView(object):

   
    def getEventManager(self):
        """Return the current event manager for this object.
        """
        return self.ZenEventManager


    def getEventHistory(self):
        """Return the current event history for this object.
        """
        return self.ZenEventHistory


    def getResultFields(self):
        return self.getEventManager().lookupManagedEntityResultFields(
                                                                self.event_key) 
        

    def getEventList(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.getEventManager().getEventListME(self, **kwargs)
        

    def getEventHistoryList(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.getEventHistory().getEventListME(self, **kwargs)
        

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
                                                        
    
    def getEventSummary(self, acked=None):
        """Return an event summary list for this managed entity.
        """
        return self.getEventManager().getEventSummaryME(self, acked)

    
    def getStatusCssClass(self, status):
        """Return the css class for a status number.
        """
        return self.getEventManager().getStatusCssClass(status) 

    
    #security.declareProtected('Manage Events','manage_deleteEvents')
    def manage_deleteEvents(self, evids=(), REQUEST=None):
        """Delete events form this managed entity.
        """
        self.getEventManager().manage_deleteEvents(evids)
        if REQUEST: return self.callZenScreen(REQUEST)


    #security.declareProtected('Manage Events','manage_setEventStates')
    def manage_setEventStates(self, eventState=None, evids=(), REQUEST=None):
        """Set event state form this managed entity.
        """
        self.getEventManager().manage_setEventStates(eventState, evids)
        if REQUEST: return self.callZenScreen(REQUEST)
