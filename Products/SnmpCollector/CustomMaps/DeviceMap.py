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

from CustomMap import CustomMap

class DeviceMap(CustomMap):

    deviceMap = {
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             #'.1.3.6.1.2.1.1.3.0' : 'snmpUpTime',
             '.1.3.6.1.2.1.1.4.0' : 'snmpContact',
             '.1.3.6.1.2.1.1.5.0' : 'snmpSysName',
             '.1.3.6.1.2.1.1.6.0' : 'snmpLocation',
             }

    osregex = (
        re.compile(r'- Software: (.+) \(Build'),    # windows
        re.compile(r'(\S+) \S+ (\S+)'),             # unix
    )

    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        return 1

    ciscoVersion = re.compile(r'Version (?P<ver>.+), ')
    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting system info for device %s' % device.id)
        data = snmpsess.get(self.deviceMap.keys())
        retdata = {}
        for oid in data.keys():
            key = self.deviceMap[oid]
            retdata[key] = data[oid] 
        if retdata['snmpOid'].find('.1.3.6.1.4.1.9') == 0:
            match = self.ciscoVersion.search(retdata['snmpDescr'])
            if match: retdata['osVersion'] = match.group('ver')

        descr = retdata['snmpDescr']
        for regex in self.osregex:
            m = regex.search(descr)
            if m: 
                retdata['setOSProductKey'] = " ".join(m.groups())
                break

        # allow for custom parse of DeviceMap data
        scDeviceMapParse = getattr(device, 'scDeviceMapParse', None)
        if scDeviceMapParse:
            retdata = scDeviceMapParse(device, snmpsess, log, retdata)
        return retdata
