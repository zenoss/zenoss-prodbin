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

class zWmiMonitorProperty(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        
        # Set zWmiMonitorIgnore defaults
        if not dmd.Devices.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices._setProperty("zWmiMonitorIgnore", True, type="boolean")
        else:
            dmd.Devices.zWmiMonitorIgnore = True

        try:
            win = dmd.Devices.getOrganizer("/Server/Windows")
            if not win.hasProperty("zWmiMonitorIgnore"):
                win._setProperty("zWmiMonitorIgnore", False, type="boolean")
            else:
                win.zWmiMonitorIgnore = False
        except KeyError: pass
        
        # Delete misspelled zProp
        for dc in dmd.Devices.getSubOrganizers():
            if dc.hasProperty('zWmiMonitorIgoner'):
                dc._delProperty('zWmiMonitorIgoner')

        for dev in dmd.Devices.getSubDevicesGen():
            if dev.hasProperty('zWmiMonitorIgoner'):
                dev._delProperty('zWmiMonitorIgoner')


zWmiMonitorProperty()
