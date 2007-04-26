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

Add zWmiMonitorIgnore to DeviceClass.

$Id:$
'''
import Migrate

class zPropsCleanup(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if dmd.Devices.zProdStateThreshold == 500:
            dmd.Devices.zProdStateThreshold = 300
        if dmd.Devices.hasProperty('zCollectorCollectPlugins'):
            dmd.Devices._delProperty('zCollectorCollectPlugins')
        if dmd.Devices.hasProperty('zCollectorIgnorePlugins'):
            dmd.Devices._delProperty('zCollectorIgnorePlugins')
        if dmd.Devices.hasProperty('zTransportPreference'):
            dmd.Devices._delProperty('zTransportPreference')

zPropsCleanup()
