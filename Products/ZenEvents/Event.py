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

import time
import socket

from ZenEventClasses import Heartbeat, Unknown

from Exceptions import *

Severities = 'Clear Debug Info Warning Error Critical'.split() 
Clear, Debug, Info, Warning, Error, Critical = range(6) 

def buildEventFromDict(evdict):
    """Build an event object from a dictionary.
    """
    evclass = evdict.get("eventClass", Unknown)
    if evclass == Heartbeat:
        for field in ("device", "component", "timeout"):
            if field not in evdict:
                raise ZenEventError("Required event field %s not found" % field)
        evt = EventHeartbeat(evdict['device'], evdict['component'], 
                             evdict['timeout'])
    else:
        evt = Event(**evdict)
    return evt



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
    
    def __init__(self, rcvtime=None, **kwargs):
        # not sure we need sub second time stamps
        # if we do uncomment and change event backend to use
        # double presicion values for these two fields.
        if not rcvtime:
            self.firstTime = self.lastTime = time.time()
        else:
            self.firstTime = self.lastTime = rcvtime
        self._clearClasses = []
        self._action = "status"
        self._fields = kwargs.get('fields',[])
        self.eventKey = ''
        self.manager = socket.getfqdn()
        if kwargs: self.updateFromDict(kwargs)

    
    def getEventFields(self):
        """return an array of event fields tuples (field,value)"""
        return [(x, getattr(self, x)) for x in self._fields]


    def getEventData(self):
        """return an list of event data"""
        return [ getattr(self, x) for x in self._fields]


    def updateFromFields(self, fields, data):
        """
        Update event from list of fields and list of data values.  
        They must have the same length.  To be used when pulling data 
        from the backend db.
        """
        self._fields = fields
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
        if we have specified clearClasses always return them
        if we ave a 0 severity return ourself as well.
        """
        clearcls = self._clearClasses
        evclass = getattr(self, "eventClass", None)
        sev = getattr(self, 'severity', None)
        if evclass and sev == 0: clearcls.append(self.eventClass)
        return clearcls


    def getDataList(self, fields):
        """return a list of data elements that map to the fields parameter.
        """
        return map(lambda x: getattr(self, x), fields)


    def getDedupFields(self, default):
        """Return list of dedupid fields.
        """
        return default


class EventHeartbeat(Event):
    
    eventClass = Heartbeat
    
    def __init__(self, device, component, timeout=120):
        self._fields = ("device", "component", "timeout")
        super(EventHeartbeat, self).__init__(
            device=device, component=component,timeout=timeout)
