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

__doc__="""NewRouteMap

NewRouteMap maps RFC2096 values to interface objects.

Hats off to the community for submitting this one.

$Id: RouteMap.py,v 1.8 2004/04/03 04:03:24 edahl Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]

from RouteMap import RouteMap
from CollectorPlugin import GetTableMap

class NewRouteMap(RouteMap):
    
    columns = {
        '.1' : 'id',
        '.5': 'setInterfaceIndex',
        '.11': 'metric1',
        '.4': 'setNextHopIp',
        '.6': 'routetype',
        '.7': 'routeproto',
        #'.8' : 'routeage',
        '.2': 'routemask',
    }


    snmpGetTableMaps = (
        GetTableMap('routetable', '.1.3.6.1.2.1.4.24.4.1', columns),
    )
