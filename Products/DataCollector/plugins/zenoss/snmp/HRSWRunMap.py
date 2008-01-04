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

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRFileSystemMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from CollectorPlugin import SnmpPlugin, GetTableMap
from sets import Set
import md5

class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"

    columns = {
         '.1': 'snmpindex',
         '.2': 'procName',
         '.4': '_procPath',
         '.5': 'parameters',
         }

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', '.1.3.6.1.2.1.25.4.2.1', columns),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
	
	#get the SNMP process data
        fstable = tabledata.get("hrSWRunEntry")
	
        rm = self.relMap()
        procs = Set()
	
	#get the processes defined in Zenoss
        processes = device.getDmdRoot("Processes")
        pcs = list(processes.getSubOSProcessClassesGen())
	log.debug("zenoss processes: %s" % pcs)
        pcs.sort(lambda a, b: cmp(a.sequence,b.sequence))
      
	#some debug output 
	if log.isEnabledFor(10):
	    log.debug("=== snmp process information received ===")
	    for p in fstable.keys():
		log.debug("snmpidx: %s\tprocess: %s" % (p, fstable[p]))
	
	    log.debug("=== processes stored/defined in Zenoss ===")
	    for p in pcs:
		log.debug("%s\t%s" % (p.id, p.regex))
	
	for proc in fstable.values():
            om = self.objectMap(proc)
            ppath = getattr(om, '_procPath', False) 
            if ppath and ppath.find('\\') == -1:
                om.procName = om._procPath
            if not getattr(om, 'procName', False): 
                log.warn("Skipping process with no name")
                continue
            if not getattr(om, 'parameters', False):
                om.parameters = ''

            fullname = (om.procName + " " + om.parameters).rstrip()
	    log.debug("current process: %s" % fullname)
            
	    for pc in pcs:
                if pc.match(fullname):
                    om.setOSProcessClass = pc.getPrimaryDmdId()
                    id = om.procName
                    parameters = om.parameters.strip()
                    if parameters and not pc.ignoreParameters:
                        parameters = md5.md5(parameters).hexdigest()
                        id += ' ' + parameters
                    om.id = self.prepId(id)
                    if id not in procs:
                        procs.add(id)
			log.debug("adding %s" % fullname)
                        rm.append(om)
                    break
            
        return rm


