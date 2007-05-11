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

__doc__="""RouteMap

RouteMap maps the interface and ip tables to interface objects

$Id: RouteMap.py,v 1.8 2004/04/03 04:03:24 edahl Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]

from CollectorPlugin import SnmpPlugin, GetTableMap

class RouteMap(SnmpPlugin):
    
    maptype = "RouteMap"
    relname = "routes"
    compname = "os"
    modname = "Products.ZenModel.IpRouteEntry"

    snmpGetTableMaps = (
        GetTableMap('routetable', '.1.3.6.1.2.1.4.21.1',
             {'.1': 'id',
             '.2': 'setInterfaceIndex',
             '.3': 'metric1',
             #'.4': 'metric2',
             #'.5': 'metric3',
             #'.6': 'metric4',
             '.7': 'setNextHopIp',
             '.8': 'routetype',
             '.9': 'routeproto',
             #'.10' : 'routeage',
             '.11': 'routemask',
             #'.12': 'metric5',
             }
        ),
    )



    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing routes for device %s' % device.id)
        getdata, tabledata = results
        routetable = tabledata.get("routetable")
        localOnly = getattr(device, 'zRouteMapCollectOnlyLocal', False)
        indirectOnly = getattr(device, 'zRouteMapCollectOnlyIndirect', False)
        rm = self.relMap()
        for route in routetable.values():
            om = self.objectMap(route)
            om.routemask = self.maskToBits(om.routemask)
            om.setTarget = om.id + "/" + str(om.routemask)
            om.id = om.id + "_" + str(om.routemask)
            if om.routemask == 32: continue
            routeproto = getattr(om, 'routeproto', 'other')
            om.routeproto = self.mapSnmpVal(routeproto, self.routeProtoMap)
            if localOnly and om.routeproto != 'local':
                continue
            if not hasattr(om, 'routetype'): 
                continue    
            om.routetype = self.mapSnmpVal(om.routetype, self.routeTypeMap)
            if indirectOnly and om.routetype != 'indirect':
                continue
            rm.append(om)
        return rm
  
    
    def mapSnmpVal(self, value, map):
        if len(map)+1 >= value:
            value = map[value-1]
        return value


    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')
