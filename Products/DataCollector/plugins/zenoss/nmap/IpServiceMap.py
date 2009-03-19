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

__doc__="""IpServiceMap

IpServiceMap uses nmap to model the list of listening TCP ports from any
device. It should be used when zenoss.snmp.IpServiceMap won't work due to
IPv6 listeners or if a device has no SNMP support.

This plugin should deprecate zenoss.portscan.IpServiceMap as it performs
much better."""

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.ZenUtils.Utils import zenPath
from twisted.internet.utils import getProcessOutput
import re

NMAPDEFAULTS = "-p 1-1024;-sT;--open;-oG -"
class IpServiceMap(PythonPlugin):
    
    transport = "python"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = PythonPlugin.deviceProperties + (
        'zNmapPortscanOptions',)

    def collect(self, device, log):
        nmapoptions = getattr(device, 'zNmapPortscanOptions', NMAPDEFAULTS) 
        nmapoptions = nmapoptions.split(";") 
        nmapoptions.append(device.manageIp)
        log.info("running nmap plugin with options: %s " % (nmapoptions))
        return getProcessOutput(zenPath('libexec', 'nmap'), nmapoptions)

    def process(self, device, results, log):
        rm = self.relMap()
        line = results.split('\n')[1]
        portMatch = re.compile('^(\d+)\/open\/tcp')
        for section in line.split(' '):
            match = portMatch.search(section)
            if not match: continue
            port = int(match.groups()[0])
            om = self.objectMap()
            om.id = 'tcp_%05d' % port
            om.ipaddresses = ['0.0.0.0',]
            om.protocol = 'tcp'
            om.port = port
            om.setServiceClass = {'protocol': 'tcp', 'port':port}
            om.discoveryAgent = self.name()
            rm.append(om)
        
        return rm
