#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CricketRouter

Mixin to provide cricket targettype id for routers

$Id: CricketRouter.py,v 1.3 2003/11/06 17:42:03 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import re

class CricketRouter:
    
    routermap = {
        '12\d\d\d|10\d\d\d' : 'CiscoVeryBigRouter',
        '72\d\d|75\d\d' : 'CiscoBigRouter',
        '36\d\d|26\d\d' : 'CiscoMedRouter',
        '650\d|35\d\d' : 'CiscoSimpleRouter',
    }
    
    def cricketDeviceType(self):
        objpaq = self.primaryAq()
        deviceType = getattr(objpaq, 'zCricketDeviceType', "Device")
        if deviceType != "Device": return deviceType
        for regex in self.routermap.keys():
            if re.search(regex, self.getModelName()):
                return self.routermap[regex]
