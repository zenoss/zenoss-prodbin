###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import re

from CommandPlugin import CommandPlugin

class Linux_ifconfig(CommandPlugin):
    """
    Linux_ifconfig maps a linux ifconfig command to the interfaces relation.
    """
    maptype = "InterfaceMap" 
    command = 'ifconfig'
    compname = "os"
    relname = "interfaces"
    modname = "Products.ZenModel.IpInterface"

    ifstart = re.compile(
        "^(\S+)\s+Link encap:(.+)HWaddr (\S+)"
        "|^(\S+)\s+Link encap:(.+)"
        ).search
    v4addr = re.compile("inet addr:(\S+).*Mask:(\S+)").search
    flags = re.compile("^(.*) MTU:(\d+)\s+Metric:.*").search


    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1


    def process(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        for line in rlines:
            m = self.ifstart(line) 
            if m:
                # start new interface and get name, type, and macaddress
                iface = self.objectMap()
                rm.append(iface)
                if m.lastindex == 3:
                    name, itype, iface.macaddress=m.groups()[:3]
                else:
                    name, itype = m.groups()[3:]
                iface.type = itype.strip()
                # Left iface.name in place, but added
                # iface.title for consistency
                iface.title = name
                iface.name = name
                iface.id = self.prepId(name)
                continue
            m = self.v4addr(line)
            if m:
                # get ip and netmask
                ip, netmask = m.groups()
                netmask = self.maskToBits(netmask)
                iface.setIpAddresses = ["%s/%s" % (ip, netmask)]
            m = self.flags(line)
            if m:
                # get adminStatus, operStatus, and mtu
                flags, mtu = m.groups()
                if "UP" in flags: iface.operStatus = 1
                else: iface.operStatus = 2
                if "RUNNING" in flags: iface.adminStatus = 1
                else: iface.adminStatus = 2
                iface.mtu = int(mtu)
        return rm
