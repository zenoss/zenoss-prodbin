#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RouteMap

RouteMap maps the interface and ip tables to interface objects

$Id: RouteMap.py,v 1.8 2004/04/03 04:03:24 edahl Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]

import re

from Products.ZenUtils.IpUtil import maskToBits

from CustomRelMap import CustomRelMap

class RouteMap(CustomRelMap):

    routeTableOid = '.1.3.6.1.2.1.4.21.1'
    routeMap = {
             '.1': 'id',
             '.2': '_ifindex',
             '.3': 'metric1',
             #'.4': 'metric2',
             #'.5': 'metric3',
             #'.6': 'metric4',
             '.7': 'setNextHop',
             '.8': 'routetype',
             '.9': 'routeproto',
             #'.10' : 'routeage',
             '.11': 'routemask',
             #'.12': 'metric5',
             }

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    def __init__(self):
        CustomRelMap.__init__(self, 'routes', 'Confmon.IpRouteEntry')



    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        return 1


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting routes for device %s' % device.id)
        bulk=0
        if device.snmpOid.find('.1.3.6.1.4.1.9') > -1:
            bulk=1
        routetable = snmpsess.collectSnmpTableMap(self.routeTableOid,
                                                  self.routeMap, bulk)
        #routetable = snmpsess.snmpTableMap(routetable, self.routeMap)
        networks = device.Networks #aq
        ifdict = device.getDeviceInterfaceIndexDict()
        localOnly = getattr(device, 'zRouteMapCollectOnlyLocal', 1)
        indirectOnly = getattr(device, 'zRouteMapCollectOnlyIndirect', 1)
        datamaps = []
        for route in routetable.values():
            route['routemask'] = maskToBits(route['routemask'])
            if route['routemask'] == 32: continue
            route['routeproto'] = self.mapSnmpVal(route['routeproto'], 
                                                    self.routeProtoMap)
            if localOnly and route['routeproto'] != 'local':
                continue
            route['routetype'] = self.mapSnmpVal(route['routetype'], 
                                                    self.routeTypeMap)
            if indirectOnly and route['routetype'] != 'indirect':
                continue
            route = self.mapInterface(ifdict, route)
            datamaps.append(route)
        return datamaps
  
    def mapInterface(self, ifdict, route):
        #try:
        ifindex = int(route['_ifindex'])
        if ifdict.has_key(ifindex):
            route['setInterface'] = ifdict[ifindex]
        #except:
        return route
    
    def mapSnmpVal(self, value, map):
        if len(map)+1 >= value:
            value = map[value-1]
        return value


    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')
