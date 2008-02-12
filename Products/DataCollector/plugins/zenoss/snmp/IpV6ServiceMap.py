###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""IpV6ServiceMap

IpV6ServiceMap creates IpV4 Services from IPV6 descriptions that allow
all incomming requests (address ::).

"""

from CollectorPlugin import SnmpPlugin, GetTableMap

import logging
log = logging.getLogger('zen.IpV6ServiceMap')

class IpV6ServiceMap(SnmpPlugin):

    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = \
                SnmpPlugin.deviceProperties + ('zIpServiceMapMaxPort',)
                
    snmpGetTableMaps = (
        GetTableMap('tcplisten', '.1.3.6.1.2.1.6.20.1.4',
                    {'.1':'v4', '.2':'v6'}),
        GetTableMap('udpendpoint', '.1.3.6.1.2.1.7.7.1.8',
                    {'.1':'v4', '.2':'v6'}),
    ) 
    
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        tcplisten = tabledata.get("tcplisten")
        udpendpoint = tabledata.get("udpendpoint")
        rm = self.relMap()
        maxport = getattr(device, 'zIpServiceMapMaxPort', 1024)

        #tcp services
        tcpports = {}
        for oid, value in tcplisten.items():
            log.debug("tcp new %s %s" % (oid,value))
            oidar = oid.split('.')
            port = int(oidar[-1])
            if port > maxport or port < 1: continue

            addr = ''
            if value.has_key('v4'): #ipv4 binding
                addr = '.'.join(oidar[-5:-1])
            elif value.has_key('v6'): #ipv6 binding
                addr = '.'.join(oidar[-17:-1])
                if addr == '0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 
                    addr = '0.0.0.0'
                else:
                    # can't handle v6 properly yet
                    continue 
            else:
                 # wha?
                continue

            om = tcpports.get(port, None)
            if om:
                if not addr in om.ipaddresses:
                    om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.id = 'tcp_%05d' % port
                om.ipaddresses = [addr,]
                om.protocol = 'tcp'
                om.port = port
                om.setServiceClass = {'protocol': 'tcp', 'port':port}
                om.discoveryAgent = self.name()
                tcpports[port] = om
                rm.append(om)

        #udp services
        udpports = {}
        for oid, value in udpendpoint.items():
            print "udp new %s %s" % (oid,value)
            oidar = oid.split('.')
            port = 0
            if port > maxport or port < 1: continue

            addr = ''
            if value.has_key('v4'): #ipv4 binding
                port = int(oidar[16])
                addr = '.'.join(oidar[12:16])
            elif value.has_key('v6'): #ipv4 binding
                port = int(oidar[28])
                addr = '.'.join(oidar[12:28])
                if addr == '0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0': 
                    addr = '0.0.0.0'
                else:
                     # can't handle v6 properly yet
                    continue
            else:
                # wha?
                continue

            om = udpports.get(port, None)
            if om:
                if not addr in om.ipaddresses:
                    om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.id = 'udp_%05d' % port
                om.ipaddresses = [addr,]
                om.protocol = 'udp'
                om.port = port
                om.setServiceClass = {'protocol': 'udp', 'port':port}
                om.discoveryAgent = self.name()
                udpports[port] = om
                rm.append(om)
        return rm


