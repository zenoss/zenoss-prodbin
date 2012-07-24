##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
    deviceProperties = LinuxCommandPlugin.deviceProperties + (
           'zInterfaceMapIgnoreNames', 'zInterfaceMapIgnoreTypes')

    ifstart = re.compile(r"^(\S+)\s+Link encap:(.+)HWaddr (\S+)"
                         "|^(\S+)\s+Link encap:(.+)")
    v4addr = re.compile(r"inet addr:(\S+).*Mask:(\S+)")
    v6addr = re.compile(r"inet6 addr: (\S+).*")
    flags = re.compile(r"^(.*) MTU:(\d+)\s+Metric:.*")
    
    def process(self, device, results, log):
        log.info('Modeler %s processing data for device %s', self.name(), device.id)
        self.log = log
        ifconfig, dmesg = results.split('__COMMAND__')
        relMap = self.parseIfconfig(ifconfig, device, self.relMap())
        relMap = parseDmesg(dmesg.lstrip(), relMap)
        return relMap
        
    def parseIfconfig(self, ifconfig, device, relMap):
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
                if miface.lastindex == 3:
                    name, itype, iface.macaddress=miface.groups()[:3]
                else:
                    name, itype = miface.groups()[3:]
                if itype.startswith("Ethernet"): itype = "ethernetCsmacd"
                iface.type = itype.strip()

                iface.interfaceName = name
                iface.id = self.prepId(name)
                dontCollectIntNames = getattr(device, 'zInterfaceMapIgnoreNames', None)
                if dontCollectIntNames and re.search(dontCollectIntNames, iface.interfaceName):
                    self.log.debug("Interface %s matched the zInterfaceMapIgnoreNames zprop '%s'",
                              iface.interfaceName, dontCollectIntNames)
                    continue

                dontCollectIntTypes = getattr(device, 'zInterfaceMapIgnoreTypes', None)
                if dontCollectIntTypes and re.search(dontCollectIntTypes, iface.type):
                    self.log.debug("Interface %s type %s matched the zInterfaceMapIgnoreTypes zprop '%s'",
                      iface.interfaceName, iface.type, dontCollectIntTypes)
                    continue

                relMap.append(iface)
                continue

            # get the IP addresses of an interface
            maddr = self.v4addr.search(line)
            if maddr and iface:
                # get IP address and netmask
                ip, netmask = maddr.groups()
                netmask = self.maskToBits(netmask)
                if not hasattr(iface, 'setIpAddresses'):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append("%s/%s" % (ip, netmask))

            maddr = self.v6addr.search(line)
            if maddr and iface:
                # get IP address
                ip = maddr.groups()[0]
                if not hasattr(iface, 'setIpAddresses'):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append(ip)

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
