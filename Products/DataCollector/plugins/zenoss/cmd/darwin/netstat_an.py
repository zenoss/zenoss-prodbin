#################################################################
#
#   Copyright (c) 2007 Zenoss Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import CommandPlugin

import string

class netstat_an(CommandPlugin):
    """
    Collect running ip services using netstat -an on a Darwin box.
    """
    maptype = "IpServiceMap" 
    command = "netstat -an | grep LISTEN"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting Ip Services for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        services = {}
        # normalize on address * means all addresses
        for line in rlines:
            aline = line.split()
            if len(aline) < 5: continue
            try:
                proto = aline[0]
                listar = aline[3].split('.')
                if len(listar) == 2:
                    addr, port = listar
                    if addr == '*':
                        addr = '0.0.0.0'
                else:
                    addr = string.join(listar[0:-1], '.')
                    port = listar[-1]


                if addr == "0.0.0.0" or not services.has_key(port):
                    services[port] = (addr, proto)
            except ValueError:
                log.exception("failed to parse ipservice information")
        ports = {}
        for port, value in services.items():
            addr, proto = value
            if proto == "raw": continue
            om = ports.get((proto, port), None)
            if om:
                om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.protocol = proto
                om.port = int(port)
                om.id = '%s_%05d' % (om.protocol,om.port)
                om.setServiceClass = {'protocol': proto, 'port':om.port}
                om.ipaddresses = [addr,]
                om.discoveryAgent = self.name()
                ports[(proto, port)] = om
                rm.append(om)
        return rm
