#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CiscoMap

CiscoMap maps cisco serialnumber information 

$Id: CiscoMap.py,v 1.3 2003/01/15 21:51:54 edahl Exp $"""

__version__ = '$Revision: 1.3 $'[11:-2]

from CustomMap import CustomMap

import re

class CiscoMap(CustomMap):

    componentName = "hw"

    ciscoMap = {
             '.1.3.6.1.4.1.9.5.1.2.19.0':'serialNumber',
             }
   
    #Cisco model names that support serial number collection
    modelcheck = re.compile(r'UBR|12\d16|720\d').search
    
    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        retdata = 0
        if (device.snmpOid.find('.1.3.6.1.4.1.9') > -1 and 
            self.modelcheck(device.model.getRelatedId())):
            retdata = 1
        return retdata

    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting cisco info for device %s' % device.id)
        data = snmpsess.get(self.ciscoMap.keys())
        retdata = {}
        for oid in data.keys():
            key = self.ciscoMap[oid]
            retdata[key] = data[oid] 
        return retdata
