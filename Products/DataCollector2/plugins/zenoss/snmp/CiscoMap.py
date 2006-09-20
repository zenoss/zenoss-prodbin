#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CiscoMap

CiscoMap maps cisco serialnumber information 

$Id: CiscoMap.py,v 1.3 2003/01/15 21:51:54 edahl Exp $"""

__version__ = '$Revision: 1.3 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetMap

class CiscoMap(SnmpPlugin):

    maptype = "CiscoDeviceMap" 

    snmpGetMap = GetMap({ 
             '.1.3.6.1.4.1.9.5.1.2.19.0':'setHWSerialNumber',
             })
   
    #Cisco model names that support serial number collection
    modelcheck = re.compile(r'3550|UBR|12\d16|720\d').search
    
    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return (device.snmpOid.startswith('.1.3.6.1.4.1.9')
                and self.modelcheck(device.hw.getProductName()))

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing cisco info for device %s' % device.id)
        getdata, tabledata = results
        return self.objectMap(getdata)
