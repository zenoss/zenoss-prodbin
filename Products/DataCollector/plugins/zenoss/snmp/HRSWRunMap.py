##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""HRSWRunMap

HRSWRunMap maps the processes running on the system to OSProcess objects.
Uses the HOST-RESOURCES-MIB OIDs.

"""

import re
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap
from Products.ZenModel.OSProcess import getProcessIdentifier

HRSWRUNENTRY = '.1.3.6.1.2.1.25.4.2.1'

class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    deviceProperties = SnmpPlugin.deviceProperties + ('getOSProcessMatchers',)

    columns = {
         '.2': 'procName',
         '.4': '_procPath',
         '.5': 'parameters',
         }

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', HRSWRUNENTRY, columns),
    )

    def process(self, device, results, log):
        """
        Process the SNMP information returned from a device
        """
        log.info('Processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)
        
        #get the SNMP process data
        pidtable = tabledata.get("hrSWRunEntry")
        if pidtable is None:
            log.error("Unable to get data for %s from hrSWRunEntry %s"
                          " -- skipping model", HRSWRUNENTRY, device.id)
            return None

        log.debug("=== Process information received ===")
        for p in sorted(pidtable.keys()):
            log.debug("snmpidx: %s\tprocess: %s" % (p, pidtable[p]))

        if not pidtable.values():
            log.warning("No process information from hrSWRunEntry %s",
                        HRSWRUNENTRY)
            return None

        for matcher in device.getOSProcessMatchers:
            try:
                regex = re.compile(matcher['regex'])
                matcher['regex'] = regex.search
            except Exception:
                log.warning("Invalid process regex '%s' -- ignoring",
                            matcher['regex'])

        found = {}
        rm = self.relMap()
        for proc in pidtable.values():
            om = self.objectMap(proc)
            ppath = getattr(om, '_procPath', False) 
            if ppath and ppath.find('\\') == -1:
                om.procName = om._procPath
            if not getattr(om, 'procName', False): 
                log.warn("Skipping process with no name")
                continue
            om.parameters = getattr(om, 'parameters', '')

            for matcher in device.getOSProcessMatchers:

                if matcher['ignoreParametersWhenModeling']: 
                    fullname = om.procName 
                else: 
                    fullname = (om.procName + ' ' + om.parameters).rstrip()

                if not matcher['regex'](fullname):
                    continue

                om.setOSProcessClass = matcher['getPrimaryDmdId']
                id = getProcessIdentifier(om.procName, None if matcher['ignoreParametersWhenModeling'] else om.parameters)
                om.id = self.prepId(id)

                if om.id not in found:
                    found[om.id] = True
                    rm.append(om)

                # Stop once a match is found.
                break

        return rm
