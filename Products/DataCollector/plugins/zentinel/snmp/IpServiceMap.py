#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""IpServiceMap

IpServiceMap maps the interface and ip tables to interface objects

$Id: IpServiceMap.py,v 1.8 2004/04/03 04:03:24 edahl Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]


from CollectorPlugin import SnmpPlugin, GetTableMap

class IpServiceMap(SnmpPlugin):

    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"

    snmpGetTableMaps = (
        GetTableMap('tcptable', '.1.3.6.1.2.1.6.13.1', {'.1':'state'}),
        GetTableMap('udptable', '.1.3.6.1.2.1.7.5.1', {'.1':'addr'}),
    ) 
    
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing Ip Services for device %s' % device.id)
        getdata, tabledata = results
        tcptable = tabledata.get("tcptable")
        udptable = tabledata.get("udptable")
        rm = self.relMap()
        #tcp services
        tcpports = {}
        for oid, value in tcptable.items():
            if value['state'] != 2: continue
            oidar = oid.split('.')
            addr = '.'.join(oidar[-10:-6])
            port = int(oidar[-6])
            if port <= 0: continue
            om = tcpports.get(port, None)
            if om:
                om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.id = 'tcp-%05d' % port
                om.ipaddresses = [addr,]
                om.setPort = port
                om.setProtocol = 'tcp'
                om.discoveryAgent = self.name()
                tcpports[port] = om
                rm.append(om)

        #udp services
        udpports = {}
        for oid, value in udptable.items():
            oid = oid.split('.')
            port = int(oid[-1])
            if port <= 0: continue
            addr = value['addr']
            om = udpports.get(port, None)
            if om:
                om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.id = 'udp-%05d' % port
                om.ipaddresses = [addr,]
                om.setPort = port
                om.setProtocol = 'udp'
                om.discoveryAgent = self.name()
                udpports[port]=om
                rm.append(om)
        return rm


