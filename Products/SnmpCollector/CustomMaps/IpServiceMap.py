#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""IpServiceMap

IpServiceMap maps the interface and ip tables to interface objects

$Id: IpServiceMap.py,v 1.8 2004/04/03 04:03:24 edahl Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]

import re

from CustomRelMap import CustomRelMap

class IpServiceMap(CustomRelMap):

    remoteClass = "Products.ZenModel.IpService"
    relationshipName = "ipservices"
    componentName = "os"

    connTcpStateOid = '.1.3.6.1.2.1.6.13.1.1'
    connUdpOid = '.1.3.6.1.2.1.7.5.1.1'
    
    
    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        return 1


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting Ip Services for device %s' % device.id)
        datamaps = []
        #tcp services
        #tcpports = {}
        oid = self.connTcpStateOid
        while 1:
            data = snmpsess.getnext(oid)
            value = data.values()[0]
            if value > 2: break
            oid = data.keys()[0]
            serv = {}
            oidar = oid.split('.')
            addr = '.'.join(oidar[-10:-6])
            port = int(oidar[-6])
            if port <= 0: continue
            if port > 1024: break
            #if port > 1024 or tcpports.has_key(port): continue
            #if addr == '0.0.0.0': tcpports[port]=1
            #tcpports[port]=1
            serv['id'] = 'tcp-%s.%05d' % (addr, port)
            serv['ipaddress'] = addr
            serv['setPort'] = port
            serv['setProtocol'] = 'tcp'
            serv['discoveryAgent'] = 'IpServiceMap-' + __version__
            datamaps.append(serv)

        #udp services
        udptable = snmpsess.getTable(self.connUdpOid)
        udpports = {}
        for oid,addr in udptable.items():
            serv = {}
            oid = oid.split('.')
            port = int(oid[-1])
            if port <= 0 or port > 1024 or udpports.has_key(port): continue
            #if addr == '0.0.0.0': udpports[port]=1
            udpports[port]=1
            serv['id'] = 'udp-%s.%05d' % (addr, port)
            serv['ipaddress'] = addr
            serv['setPort'] = port
            serv['setProtocol'] = 'udp'
            serv['discoveryAgent'] = 'IpServiceMap-' + __version__
            datamaps.append(serv)

        return datamaps


