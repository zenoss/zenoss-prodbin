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

from datetime import datetime, timedelta

CLEAR=0
DEBUG=10
INFORMATION=20
WARNING=30
CRITICAL=40
FATAL=50


requiredFields = ("device","summary",)


def EventFromDict(eventdict):
    for field in requiredFields:
        if not eventdict.has_key(field): raise "BadEventError"
    return apply(Event, [], eventdict)
   


class Event(object):
   
    fields = ['device', 'startdate', 'enddate', 'lastupdate',
                'summary', 'severity', 'classid', 'ipaddress',
                'monitor', 'monitorhost', ]

    def __init__(self, device, *args, **kargs):
        self._oid = None
        self._serial = 0L
        self.device = device
        self.startdate = datetime.utcnow()
        self.lastupdate = datetime.utcnow()
        self.enddate = None
        self.summary = ""
        self.severity = -1
        self.classid = -1 
        self.ipaddress = ""
        self.monitor = ""
        self.monitorhost = ""

        for k, v in kargs.items():
            if not k in self.fields:
                self.fields.append(k)
            setattr(self, k, v)

    def getfields(self):
        return self.fields


    def gettext(self):
        """return all event data as a big text string"""
        text = [] 
        for field in self.getfields():
            text.append(str(getattr(self, field)))
        return " ".join(text)

    def getdict(self):
        evdict = {}
        for field in self.getfields():
            evdict[field] = getattr(self, field)
        return evdict
    
    def getarray(self):
        evarray = []
        for field in self.getfields():
            evarray.append((field, getattr(self, field)))
        return evarray
