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

class ZenEvent(object):
    
    def __init__(self, device, *args, **kargs):
        self.oid = None
        self.device = device
        self.startdate = datetime.utcnow()
        self.lastupdate = datetime.utcnow()
        self.enddate = None
        self.summary = ""
        self.severity = 0
        self.classid = 0
        
        self.fields = ["device",
                        "startdate", "lastupdate", "enddate", 
                        "summary", "severity", "classid"]

        for k, v in kargs.items():
            if k not in self.fields:
                self.fields.append(k)
            setattr(self, k, v)

    def getfields(self):
        return self.fields



