##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """netstat_an
Collect running IP services using netstat -a
"""

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin

class netstat_an(LinuxCommandPlugin):
    maptype = "IpServiceMap" 
    command = "netstat -an | grep ':\\*'"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = LinuxCommandPlugin.deviceProperties + (
           'zIpServiceMapMaxPort', )


    def process(self, device, results, log):
        log.info('Modeler %s processing data for device %s', self.name(), device.id)

        if not results.strip(): # No output
            log.error("No output from the command: %s", self.command)
            return

        try:
            maxport = getattr(device, 'zIpServiceMapMaxPort', 1024)
            maxport = int(maxport)
        except ValueError:
            maxport = 1024

        rm = self.relMap()
        ports = {}
        for line in results.split("\n"):
            aline = line.split()
            if len(aline) < 5: continue
            try:
                proto = aline[0]
                if proto == "raw":
                    continue
                listar = aline[3].split(":")
                addr = port = ""
                if len(listar) == 2:
                    addr, port = listar
                elif len(listar) == 4:
                    addr = "0.0.0.0"
                    port = listar[-1]
                else:
                    continue

                log.debug("Got %s %s port %s", addr, proto, port)
                if addr == "127.0.0.1" or not port: # Can't monitor things we can't reach
                    continue

                port = int(port)
                if port > maxport:
                    log.debug("Ignoring entry greater than zIpServiceMapMaxPort (%s): %s %s %s",
                              maxport, addr, proto, port)
                    continue
            except ValueError:
                log.exception("Failed to parse IPService information '%s'",
                              line)
                continue

            om = ports.get((proto, port), None)
            if om:
                if addr in om.ipaddresses:
                    continue
                log.debug("Adding %s to the list of addresses listening to %s port %s",
                          addr, proto, port)
                om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.protocol = proto
                om.port = int(port)
                om.id = '%s_%05d' % (om.protocol,om.port)
                log.debug("Found %s listening to %s port %s (%s)",
                          addr, proto, port, om.id)
                om.setServiceClass = {'protocol': proto, 'port':om.port}
                om.ipaddresses = [addr,]
                om.discoveryAgent = self.name()
                ports[(proto, port)] = om
                rm.append(om)

        log.debug("Found %d IPServices", len(ports.keys()))
        return rm
