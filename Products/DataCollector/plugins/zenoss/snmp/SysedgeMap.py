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

__doc__ = """SysedgeMap

Gather Empire SysEDGE disk OS and licensing information.

"""

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin

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
