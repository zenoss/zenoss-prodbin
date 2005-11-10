
class ManagedEntity(object):

   
    def getEventManager(self):
        """Return the current event manager for this object.
        """
        return self.ZenEventManager


    def getEventHistory(self):
        """Return the current event history for this object.
        """
        return self.ZenEventHistory


    def getResultFields(self):
        return self.getEventManager().lookupManagedEntityResultFields(self) 
        

    def getEventList(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.getEventManager().getEventListME(self, **kwargs)
        

    def getEventHistoryList(self, **kwargs):
        """Return the current event list for this managed entity.
        """
        return self.getEventHistory().getEventListME(self, **kwargs)
        

    def getStatus(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        return self.getEventManager().getStatusME(self, statclass, **kwargs)


    def getStatusString(self, statclass, **kwargs):
        """Return the status number for this device of class statClass.
        """
        return self.convertStatus(
                self.getEventManager().getStatusME(self, statclass, **kwargs))
                                                        

    def getEventSummary(self, acked=None):
        """Return an event summary list for this managed entity.
        """
        return self.getEventManager().getEventSummaryME(self, acked)

    
    def getStatusCssClass(self, status):
        """Return the css class for a status number.
        """
        return self.getEventManager().getStatusCssClass(status) 


