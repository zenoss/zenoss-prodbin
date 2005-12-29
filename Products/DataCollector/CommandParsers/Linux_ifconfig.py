#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: Uname_A.py,v 1.2 2003/10/01 23:40:51 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]


import re

from Products.ZenUtils.IpUtil import isip, maskToBits

from CommandParser import CommandParser

class Linux_ifconfig(CommandParser):
    
    command = 'ifconfig'
    componentName = "os"

    ifstart = re.compile(
        "^(\S+)\s+Link encap:(.+)HWaddr (\S+)"
        "|^(\S+)\s+Link encap:(.+)"
        ).search
    v4addr = re.compile("inet addr:(\S+).*Mask:(\S+)").search
    flags = re.compile("^(.*) MTU:(\d+)\s+Metric:.*").search
    
    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1

    def parse(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        rm = self.newRelationshipMap("interfaces", "os")
        rlines = results.split("\n")
        for line in rlines:
            m = self.ifstart(line) 
            if m:
                # start new interface and get name, type, and macaddress
                iface = self.newObjectMap("ZenModel.IpInterface")
                if m.lastindex == 3:
                    name, itype, iface['macaddress']=m.groups()[:3]
                else:
                    name, itype = m.groups()[3:]
                iface['type'] = itype.strip()
                iface['name'] = name
                iface['id'] = self.prepId.sub('_', name)
                continue
            m = self.v4addr(line)
            if m:
                # get ip and netmask
                ip, netmask = m.groups()
                netmask = maskToBits(netmask)
                iface['setIpAddresses'] = "%s/%s" % (ip, netmask)
            m = self.flags(line)
            if m:
                # get adminStatus, operStatus, and mtu
                flags, mtu = m.groups()
                if "UP" in flags: iface['operStatus'] = 1
                else: iface['operStatus'] = 2
                if "RUNNING" in flags: iface['adminStatus'] = 1
                else: iface['adminStatus'] = 2
                iface['mtu'] = int(mtu)
            rm.append(iface)
            #log.debug('Adding route %s' % route['setTarget'])
        return rm
