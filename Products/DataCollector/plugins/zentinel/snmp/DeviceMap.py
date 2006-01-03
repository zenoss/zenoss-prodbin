#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""DeviceMap

DeviceMap maps the interface and ip tables to interface objects

$Id: DeviceMap.py,v 1.9 2003/11/19 03:14:53 edahl Exp $"""

__version__ = '$Revision: 1.9 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetMap

class DeviceMap(SnmpPlugin):

    maptype = "DeviceMap" 

    snmpGetMap = GetMap({ 
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             #'.1.3.6.1.2.1.1.3.0' : 'snmpUpTime',
             '.1.3.6.1.2.1.1.4.0' : 'snmpContact',
             '.1.3.6.1.2.1.1.5.0' : 'snmpSysName',
             '.1.3.6.1.2.1.1.6.0' : 'snmpLocation',
             })

    osregex = (
        re.compile(r'- Software: (.+) \(Build'),    # windows
        re.compile(r'(\S+) \S+ (\S+)'),             # unix
    )

    
    ciscoVersion = re.compile(r'Version (?P<ver>.+), ')
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing system info for device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)

        if om.snmpOid.find('.1.3.6.1.4.1.9') == 0:
            match = self.ciscoVersion.search(om.snmpDescr)
            if match: om.osVersion = match.group('ver')

        if getattr(device, "zSnmpHWDiscovery", True):
            om.setHWProductKey = om.snmpOid

        if getattr(device, "zSnmpOSDiscovery", True):
            descr = om.snmpDescr
            for regex in self.osregex:
                m = regex.search(descr)
                if m: 
                    om.setOSProductKey = " ".join(m.groups())
                    break

        # allow for custom parse of DeviceMap data
        scDeviceMapParse = getattr(device, 'scDeviceMapParse', None)
        if scDeviceMapParse:
            om = scDeviceMapParse(device, om)
        return om
