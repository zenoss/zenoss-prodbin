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

import re

from CollectorPlugin import CommandPlugin

class ifconfig(CommandPlugin):
    """
    ifconfig maps a linux ifconfig command to the interfaces relation.
    """
    maptype = "InterfaceMap" 
    command = '/sbin/ifconfig'
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
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        iface = None
        for line in rlines:

            # reset state to no interface
            if not line.strip(): 
                iface = None

            # new interface starting
            miface = self.ifstart(line) 
            if miface:
                # start new interface and get name, type, and macaddress
                iface = self.objectMap()
                rm.append(iface)
                if miface.lastindex == 3:
                    name, itype, iface.macaddress=miface.groups()[:3]
                else:
                    name, itype = miface.groups()[3:]
                if itype.startswith("Ethernet"): itype = "ethernetCsmacd"
                iface.type = itype.strip()
                iface.interfaceName = name
                iface.id = self.prepId(name)
                continue
    
            # get the ip address of an interface
            maddr = self.v4addr(line)
            if maddr and iface:
                # get ip and netmask
                ip, netmask = maddr.groups()
                netmask = self.maskToBits(netmask)
                iface.setIpAddresses = ["%s/%s" % (ip, netmask)]

            # get the state UP/DOWN of the interface
            mstatus = self.flags(line)
            if mstatus and iface:
                # get adminStatus, operStatus, and mtu
                flags, mtu = mstatus.groups()
                if "UP" in flags: iface.operStatus = 1
                else: iface.operStatus = 2
                if "RUNNING" in flags: iface.adminStatus = 1
                else: iface.adminStatus = 2
                iface.mtu = int(mtu)
        return rm
