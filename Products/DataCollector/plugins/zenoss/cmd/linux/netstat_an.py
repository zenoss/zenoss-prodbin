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

from CollectorPlugin import CommandPlugin

class netstat_an(CommandPlugin):
    """
    Collect running ip services using netstat -an on a linux box.
    """
    maptype = "IpServiceMap" 
    command = "netstat -an | grep ':\\*'"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


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
                listar = aline[3].split(":")
                addr = port = ""
                if len(listar) == 2:
                    addr, port = listar
                elif len(listar) == 4:
                    addr = "0.0.0.0"
                    port = listar[-1]
                if not port: continue
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
