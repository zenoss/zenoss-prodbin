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

__doc__='''

Set zWmiMonitorIgnore defaults
Remove zWmiMonitorIgoner

$Id:$
'''
import Migrate

def getDeviceClasses(deviceClass, deviceClasses=[]):
    deviceClasses.append(deviceClass)
    for child in deviceClass.children():
        getDeviceClasses(child, deviceClasses)
    return deviceClasses
    
class zWmiMonitorProperty(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        
        # Set zWmiMonitorIgnore defaults
        if not dmd.Devices.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices._setProperty("zWmiMonitorIgnore", True, type="boolean")
        else:
            dmd.Devices.zWmiMonitorIgnore = True
        
        if not dmd.Devices.Server.Windows.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices.Server.Windows._setProperty("zWmiMonitorIgnore", False, type="boolean")
        else:
            dmd.Devices.Server.Windows.zWmiMonitorIgnore = False
        
        # Delete misspelled zProp
        for dc in getDeviceClasses(dmd.Devices, []):
            if dc.hasProperty('zWmiMonitorIgoner'):
                dc._delProperty('zWmiMonitorIgoner')

        for dev in dmd.Devices.getSubDevicesGen():
            if dev.hasProperty('zWmiMonitorIgoner'):
                dev._delProperty('zWmiMonitorIgoner')


zWmiMonitorProperty()
