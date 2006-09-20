#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SysedgeMap

SysedgeMap maps the interface and ip tables to interface objects

$Id: SysedgeMap.py,v 1.6 2003/01/15 21:51:54 edahl Exp $"""

__version__ = '$Revision: 1.6 $'[11:-2]

from CollectorPlugin import SnmpPlugin, GetMap

class SysedgeMap(SnmpPlugin):

    sysedgeMap = {
             '.1.3.6.1.4.1.546.1.1.1.8.0':'snmpAgent',
             '.1.3.6.1.4.1.546.1.1.1.17.0':'sysedgeLicenseMode',
             '.1.3.6.1.2.1.25.6.3.1.2.1':'setOSProductKey',
             }


    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return False


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting sysedge info for device %s' % device.id)
        data = snmpsess.get(self.sysedgeMap.keys())
        retdata = {}
        for oid in data.keys():
            key = self.sysedgeMap[oid]
            retdata[key] = data[oid] 
            if key == 'snmpSysedgeMode':
                if data[oid] == 1:
                    retdata[key] = 'fullMode' 
                else:
                    retdata[key] = 'restrictedMode'
        return retdata
