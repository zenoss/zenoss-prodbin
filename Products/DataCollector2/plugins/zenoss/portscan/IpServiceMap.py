#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""IpServiceMap

IpServiceMap maps the interface and ip tables to interface objects

$Id: IpServiceMap.py,v 1.8 2006/06/14 04:03:24 oubiwann Exp $"""

__version__ = '$Revision: 1.8 $'[11:-2]


from CollectorPlugin import CollectorPlugin

class IpServiceMap(CollectorPlugin):

    transport = "portscan"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"

    def condition(self, device, log):
        """
        Default condition for portscan is True.
        """
        return True

    def preprocess(self, results, log):
        """
        Make sure the ports are integers.
        """
        addr = results.keys()[0]
        ports = [ int(port) for port in results[addr] ]
        return (addr, ports)

    def process(self, device, results, log):
        """
        Collect open port information from this device.
        """
        log.info('processing Ip Services for device %s' % device.id)
        addr, ports = results
        rm = self.relMap()
        for port in ports:
            om = self.objectMap()
            om.id = 'tcp_%05d' % port
            om.ipaddresses = [addr]
            om.protocol = 'tcp'
            om.port = port
            om.setServiceClass = {'protocol': 'tcp', 'port':port}
            om.discoveryAgent = self.name()
            rm.append(om)
        return rm

