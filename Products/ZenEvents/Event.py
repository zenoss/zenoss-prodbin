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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

def eventFromDb(manager, data, fields):
    """Construct an event from a database row."""
    evt = Event(manager.absolute_url_path())
    defaultFields = manager.defaultFields
    defaultLen = len(defaultFields)
    evt.data = data[:-defaultLen]
    evt.defaultdata = data[-defaultLen:]
    for i in range(len(fields)):
        setattr(evt, fields[i], data[i])
    for i in range(len(defaultFields)):
        setattr(evt, defaultFields[i], evt.defaultdata[i])
        if defaultFields[i] == manager.severityField:
            setattr(evt, defaultFields[i] + "Name", 
                manager.convert(manager.severityField, evt.defaultdata[i]))
    if not hasattr(evt, "Serial"): evt.Serial = evt.ServerSerial
    return evt
    

class Event(object):
    """
    Class that represents an event in our system.
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
 
    def __init__(self, baseUrl=""):
        self.baseUrl = baseUrl
        self.bgcolor = "#FFFFFF"
        self.fgcolor = "#000000"
        self.Severity = 0
        self.SeverityName = "Clear"
        self.Acknowledged = False
        
  
    def getEventDetailHref(self):
        """build an href to call the detail of this event"""
        params = "/viewNcoEventFields?serverserial=%d&servername=%s" % (
                        self.ServerSerial, self.ServerName)
        return self.baseUrl + params


    def getCssClass(self):
        """return the css class name to be used for this event.
        """
        acked = self.Acknowledged and "true" or "false"
        return "zenevents_%s_%s" % (self.SeverityName.lower(), acked)


    def getfieldcount(self):
        """return the number of fields"""
        return len(self.data)


    def getfield(self, index):
        """return the value of a field"""
        return self.data[index]


    def getSeverityNumber(self):
        """return the severity as an integer"""
        return self.defaultdata[1]

InitializeClass(Event)
