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
    
    def __init__(self, device, *args, **kargs):
        self._oid = None
        self.serial = 0L
        self.device = device
        self.startdate = datetime.utcnow()
        self.lastupdate = datetime.utcnow()
        self.enddate = None
        self.summary = ""
        self.severity = -1
        self.classid = -1 
        for k, v in kargs.items():
            setattr(self, k, v)

    def getfields(self):
        return filter(lambda x: x[0]!='_', dir(self))


    def gettext(self):
        """return all event data as a big text string"""
        text = ()
        for field in self.getfields():
            text.append(str(getattr(self, field)))
        return " ".join(text)
