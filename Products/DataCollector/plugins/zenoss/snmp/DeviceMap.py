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

__doc__="""DeviceMap

DeviceMap maps the interface and ip tables to interface objects

$Id: DeviceMap.py,v 1.9 2003/11/19 03:14:53 edahl Exp $"""

__version__ = '$Revision: 1.9 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetMap

class DeviceMap(SnmpPlugin):

    maptype = "DeviceMap" 

    columns = {
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             #'.1.3.6.1.2.1.1.3.0' : 'snmpUpTime',
             '.1.3.6.1.2.1.1.4.0' : 'snmpContact',
             '.1.3.6.1.2.1.1.5.0' : 'snmpSysName',
             '.1.3.6.1.2.1.1.6.0' : 'snmpLocation',
             }
    snmpGetMap = GetMap(columns)

    
    ciscoVersion = re.compile(r'Version (?P<ver>.+), ')
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        if not self.checkColumns(getdata, self.columns, log): 
            return 
        om = self.objectMap(getdata)

        if om.snmpOid.find('.1.3.6.1.4.1.9') == 0:
            match = self.ciscoVersion.search(om.snmpDescr)
            if match: om.osVersion = match.group('ver')

        # allow for custom parse of DeviceMap data
        scDeviceMapParse = getattr(device, 'scDeviceMapParse', None)
        if scDeviceMapParse:
            om = scDeviceMapParse(device, om)
        return om
