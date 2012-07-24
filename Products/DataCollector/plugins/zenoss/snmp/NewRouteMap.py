##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """NewRouteMap

NewRouteMap maps RFC2096 values to interface objects.

Hats off to the community for submitting this one.
"""
from RouteMap import RouteMap
from Products.DataCollector.plugins.CollectorPlugin import GetTableMap

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
