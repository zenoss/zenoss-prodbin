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

class NewDeviceMap(SnmpPlugin):

    maptype = "NewDeviceMap" 

    snmpGetMap = GetMap({ 
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             })

    osregex = (
        re.compile(r'- Software: (.+) \(Build'),    # windows
        re.compile(r'(\S+) \S+ (\S+)'),             # unix
    )

    def condition(self, device, log):
        """Only run if products have not been set.
        """
        return not device.os.getProductName() and not device.hw.getProductName()

    
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing system info for device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        om.setHWProductKey = om.snmpOid
        descr = om.snmpDescr
        for regex in self.osregex:
            m = regex.search(descr)
            if m: 
                om.setOSProductKey = " ".join(m.groups())
                break
        return om
