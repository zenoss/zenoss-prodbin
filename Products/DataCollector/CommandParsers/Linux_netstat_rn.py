##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: Uname_A.py,v 1.2 2003/10/01 23:40:51 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from Products.ZenUtils.IpUtil import isip, maskToBits

from CommandParser import CommandParser

TARGET=0
GATEWAY=1
NETMASK=2
FLAGS=3
INTERFACE=7

class Linux_netstat_rn(CommandParser):
    
    command = 'netstat -rn'
    componentName = "os"

    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1

    def parse(self, device, results, log):
        log.info('Collecting routes for device %s' % device.id)
        indirectOnly = getattr(device, 'zRouteMapCollectOnlyIndirect', False)
        rm = self.newRelationshipMap("routes", "os")
        rlines = results.split("\n")
        for line in rlines:
            aline = line.split()
            if len(aline) != 8 or not isip(aline[0]): continue
            route = self.newObjectMap("Products.ZenModel.IpRouteEntry")

            route['routemask'] = maskToBits(aline[NETMASK])
            if route['routemask'] == 32: continue

            if "G" in aline[FLAGS]:
                route['routetype'] = 'indirect'
            else:
                route['routetype'] = 'direct'
            if indirectOnly and route['routetype'] != 'indirect':
                continue

            route['id'] = aline[TARGET]
            route['setTarget'] = route['id'] + "/" + str(route['routemask'])
            route['id'] = route['id'] + "_" + str(route['routemask'])
            route['setInterfaceName'] = aline[INTERFACE]
            route['setNextHopIp'] = aline[GATEWAY]
            rm.append(route)
        return rm

    def description(self):
        return "run netstat -an on server to build ipservices"
