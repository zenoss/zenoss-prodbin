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

__doc__="""CiscoMap

CiscoMap maps cisco serialnumber information 

$Id: CiscoMap.py,v 1.3 2003/01/15 21:51:54 edahl Exp $"""

__version__ = '$Revision: 1.3 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetMap

class CiscoMap(SnmpPlugin):

    maptype = "CiscoDeviceMap" 

    snmpGetMap = GetMap({ 
             '.1.3.6.1.4.1.9.3.6.3.0' : 'setHWSerialNumber',
             })
   
    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return device.snmpOid.startswith('.1.3.6.1.4.1.9')


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        return self.objectMap(getdata)
