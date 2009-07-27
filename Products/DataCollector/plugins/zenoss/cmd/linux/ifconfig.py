###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """ifconfig
ifconfig maps a linux ifconfig command to the interfaces relation.
"""

import re

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin

speedPattern = re.compile(r'(\d+)\s*mbps', re.I)

def parseDmesg(dmesg, relMap):
    """
    parseDmesg to get interface speed.
    """
    for line in dmesg.splitlines():
        speedMatch = speedPattern.search(line)
        if speedMatch:
            for objMap in relMap.maps:
                if objMap.interfaceName in line:
                    objMap.speed = int(speedMatch.group(1)) * 1000000
                    break
    return relMap

class ifconfig(LinuxCommandPlugin):
    # echo __COMMAND__ is used to delimit the results
    command = '/sbin/ifconfig -a && echo __COMMAND__ && /bin/dmesg'
    compname = "os"
    relname = "interfaces"
    modname = "Products.ZenModel.IpInterface"

    ifstart = re.compile(r"^(\S+)\s+Link encap:(.+)HWaddr (\S+)"
                         "|^(\S+)\s+Link encap:(.+)")
    v4addr = re.compile(r"inet addr:(\S+).*Mask:(\S+)")
    flags = re.compile(r"^(.*) MTU:(\d+)\s+Metric:.*")
    
    def process(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        ifconfig, dmesg = results.split('__COMMAND__')
        relMap = self.parseIfconfig(ifconfig, self.relMap())
        relMap = parseDmesg(dmesg.lstrip(), relMap)
        return relMap
        
    def parseIfconfig(self, ifconfig, relMap):
        """
        Parse the output of the ifconfig -a command.
        """
        rlines = ifconfig.splitlines()
        iface = None
        for line in rlines:

            # reset state to no interface
            if not line.strip(): 
                iface = None

            # new interface starting
            miface = self.ifstart.search(line) 
            if miface:
                # start new interface and get name, type, and macaddress
                iface = self.objectMap()
                relMap.append(iface)
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
            maddr = self.v4addr.search(line)
            if maddr and iface:
                # get ip and netmask
                ip, netmask = maddr.groups()
                netmask = self.maskToBits(netmask)
                iface.setIpAddresses = ["%s/%s" % (ip, netmask)]

            # get the state UP/DOWN of the interface
            mstatus = self.flags.search(line)
            if mstatus and iface:
                # get adminStatus, operStatus, and mtu
                flags, mtu = mstatus.groups()
                if "UP" in flags: iface.operStatus = 1
                else: iface.operStatus = 2
                if "RUNNING" in flags: iface.adminStatus = 1
                else: iface.adminStatus = 2
                iface.mtu = int(mtu)

        return relMap

