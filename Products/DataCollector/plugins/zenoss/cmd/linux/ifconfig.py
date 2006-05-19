#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

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
                if itype.startswith("Ethernet"): itype = "ethernetCsmacd"
                iface.type = itype.strip()
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
