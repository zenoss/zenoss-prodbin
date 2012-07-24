##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """IpV6ServiceMap

IpV6ServiceMap creates IpV4 Services from IPV6 descriptions that allow
all incoming requests (address ::).

"""

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap

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

    def _extractAddressAndPort(self, oid, invalue):
        print "running _extractAddressAndPort"
        nullReturnValue = ('',0)
        addr, port = nullReturnValue
        try:
            oidparts = oid.split('.')

            if 'v4' in invalue: #ipv4 binding
                port = int(oidparts.pop())
                addr = '.'.join(oidparts[-4:])
            elif 'v6' in invalue: #ipv6 binding
                port = int(oidparts.pop())
                addr = '.'.join(oidparts[-16:])
                if addr == '0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0':
                    addr = '0.0.0.0'
                else:
                    # can't handle v6 properly yet
                    return nullReturnValue
            else:
                 # wha?
                return nullReturnValue

        except Exception:
            addr,port = nullReturnValue

        return addr, port

    def _processTcp(self, tcplisten):
        result = []
        for oid, value in tcplisten.items():
            log.debug("tcp new %s %s" % (oid,value))
            addr, port = self._extractAddressAndPort(oid, value)
            if not addr:
                continue

            om = self.objectMap()
            om.id = 'tcp_%05d' % port
            om.ipaddresses = [addr,]
            om.protocol = 'tcp'
            om.port = port
            om.setServiceClass = {'protocol': 'tcp', 'port':port}
            om.discoveryAgent = self.name()
            result.append(om)
        return result

    def _processUdp(self, udpendpoint):
        result = []
        for oid, value in udpendpoint.items():
            addr, port = self._extractAddressAndPort(oid, value)
            if not addr:
                continue

            om = self.objectMap()
            om.id = 'udp_%05d' % port
            om.ipaddresses = [addr,]
            om.protocol = 'udp'
            om.port = port
            om.monitor = False
            om.setServiceClass = {'protocol': 'udp', 'port':port}
            om.discoveryAgent = self.name()
            result.append(om)
        return result

    def _reduceByPort(self, maxport, rm, maps):
        ports = {}
        for map in maps:
            addr = map.ipaddresses[0]
            port = map.port
            if port > maxport: continue
            om = ports.get(port, None)
            if om:
                if not addr in om.ipaddresses:
                    om.ipaddresses.append(addr)
            else:
                ports[port] = map
                rm.append(map)


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        tcplisten = tabledata.get("tcplisten")
        udpendpoint = tabledata.get("udpendpoint")
        if tcplisten is None or udpendpoint is None: return
        rm = self.relMap()
        maxport = getattr(device, 'zIpServiceMapMaxPort', 1024)
        self._reduceByPort(maxport, rm, self._processTcp(tcplisten))
        self._reduceByPort(maxport, rm, self._processUdp(udpendpoint))
        return rm
