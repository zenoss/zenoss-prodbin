###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

#import time
import socket
import DateTime

class Event(object):
    """
    Event that lives independant of zope context.  As interface that allows
    it to be persisted to/from the event backend.
    dedupid,
    evid,
    device,
    ipAddress,
    component,
    eventClass,
    eventGroup,
    eventKey,
    facility,
    severity,
    priority,
    summary,
    stateChange,
    firstTime,
    lastTime,
    count,
    prodState,
    manager,
    agent,
    DeviceClass,
    Location,
    Systems,
    DeviceGroups,
    """
    
    def __init__(self, **kwargs):
        # not sure we need sub second time stamps
        # if we do uncomment and change event backend to use
        # double presicion values for these two fields.
        #self.firstTime = time.time()
        #self.lastTime = time.time()
        self._clearClasses = []
        self._action = "status"
        self.eventKey = ''
        self.manager = socket.getfqdn()
        if kwargs: self.updateFromDict(kwargs)

    
    def updateFromFields(self, fields, data):
        """
        Update event from list of fields and list of data values.  
        They must have the same length.  To be used when pulling data 
        from the backend db.
        """
        for i in range(len(fields)):
            setattr(self, fields[i], data[i])


    def updateFromDict(self, data):
        """Update event from dict.  Keys that don't match attributes are
        put into the detail list of the event.
        """
        for key, value in data.items():
            setattr(self, key, value)


    def clearClasses(self):
        """Return a list of classes that this event clears.
        """
        clearcls = self._clearClasses
        if hasattr(self, 'eventClass'): clearcls.append(self.eventClass)
        return clearcls


    def initTime(self, timestamp):
        """Initialize first and last time from timestamp value.
        """
        tstamp = DateTime.DateTime(timestamp)
        self.firstTime = tstamp
        self.lastTime = tstamp


    def getDataList(self, fields):
        """return a list of data elements that map to the fields parameter.
        """
        return map(lambda x: getattr(self, x), fields)
