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

__doc__="""CpuMap

Uses wmi to map cpu information on CPU objects

$Id: $"""

from Products.ZenWin.WMIPlugin import WMIPlugin
from Products.ZenUtils.Utils import prepId

class cpu(WMIPlugin):

    maptype = "CpuMap" 
    modname = "Products.ZenModel.CPU"
    relname = "cpus"
    compname = "hw"

    attrs = (
        'DeviceID', 
        'Description', 
        'Manufacturer',
        'SocketDesignation',
        'CurrentClockSpeed',
        'ExtClock',
        'CurrentVoltage',
        'L2CacheSize',
    )
    
    def queryStrings(self):
        return (
            "Select %s From Win32_Processor" %  (",".join(self.attrs)),
        )
        
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        maps = []
        rm = self.relMap()
        for cpu in results[0]:
            om = self.objectMap()
            om.id = prepId(cpu.DeviceID)
            om.setProductKey = cpu.Description
            om.setManufacturerName = cpu.Manufacturer
            om.socket = cpu.SocketDesignation
            om.clockspeed = cpu.CurrentClockSpeed
            om.extspeed = cpu.ExtClock
            om.voltage = int(cpu.CurrentVoltage) * 100
            #om.cacheSizeL1 = cpu.
            om.cacheSizeL2 = cpu.L2CacheSize
            rm.append(om)
        maps.append(rm)
        return maps
