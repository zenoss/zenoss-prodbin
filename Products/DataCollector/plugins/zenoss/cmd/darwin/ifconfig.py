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

import re, string

from CollectorPlugin import CommandPlugin

class ifconfig(CommandPlugin):
    """
    ifconfig maps a Darwin ifconfig command to the interfaces relation.
    """
    maptype = "InterfaceMap" 
    command = '/sbin/ifconfig'
    compname = "os"
    relname = "interfaces"
    modname = "Products.ZenModel.IpInterface"


    flags = re.compile(".+flags=\d+<(.+)>.+").search
    v4addr = re.compile("inet (\S+).*netmask (\S+)").search
    ether = re.compile("ether (\S+)").search


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def chunk(self, output):
        '''splits the ifconfig output into a [] where each item in the list
        represents the ifconfig output for an individual interface'''

        chunks = []
        chunk = []
        for line in output.split('\n'):
            if line.startswith('\t'):
                chunk.append(' ')
                chunk.append(line)
            else:
                section = string.join(chunk, ' ').strip()
                if len(section) > 0:
                    chunks.append(section)
                chunk = [line]

        joined = string.join(chunk, ' ').strip()
        if len(joined) > 0:
            chunks.append()

        return chunks


    def process(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        rm = self.relMap()

        for chunk in self.chunk(results):
            iface = self.objectMap()
            rm.append(iface)

            intf = chunk.split(':')[0]

            m = self.flags(chunk)
            if m:
                flags = m.groups()[0].split(',')
                if "UP" in flags: iface.operStatus = 1
                else: iface.operStatus = 2
                if "RUNNING" in flags: iface.adminStatus = 1
                else: iface.adminStatus = 2

            iface.id = self.prepId(intf)
            iface.interfaceName = intf

            maddr = self.v4addr(chunk)
            if maddr and iface:
                ip, netmask = maddr.groups()
                netmask = self.hexToBits(netmask)
                iface.setIpAddresses = ["%s/%s" % (ip, netmask)]
                
            mether = self.ether(chunk)
            if mether and iface:
                hwaddr = mether.groups()[0]
                iface.macaddress = hwaddr
                
        return rm
