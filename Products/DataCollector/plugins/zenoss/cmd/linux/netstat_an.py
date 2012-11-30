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
from Products.ZenUtils import IpUtil

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
        for line in results.splitlines():
            aline = line.split()
            if len(aline) < 5: continue
            try:
                proto, local = aline[0], aline[3]
                if proto == "raw":
                    continue
                addr, port = local.rsplit(":", 1) 
                log.debug("Got %s %s port %s", addr, proto, port)
                if not IpUtil.isRemotelyReachable(addr) or not port:
                    # Can't monitor things we can't reach
                    continue
                port = int(port)
                if port > maxport:
                    log.debug("Ignoring entry greater than " \
                              "zIpServiceMapMaxPort (%s): %s %s %s",
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
