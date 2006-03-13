#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import CommandPlugin

class netstat_an(CommandPlugin):
    """
    Collect running ip services using netstat -an on a linux box.
    """
    maptype = "IpServiceMap" 
    command = 'netstat -an | grep 0.0.0.0:*'
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"


    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1


    def process(self, device, results, log):
        log.info('Collecting Ip Services for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        services = {}
        # normalize on address 0.0.0.0 means all addresses
        for line in rlines:
            aline = line.split()
            if len(aline) < 5: continue
            try:
                proto = aline[0]
                addr, port = aline[3].split(":")
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
                om.setServiceClass = {'protocol': proto, 'port':port}
                om.ipaddresses = [addr,]
                om.discoveryAgent = self.name()
                ports[(proto, port)] = om
                rm.append(om)
        return rm
