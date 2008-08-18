###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Set zRouteMapMaxRoutes defaults

$Id:$
'''
import Migrate

class zRouteMapMaxRoutesProperty(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        
        # Set zRouteMapMaxRoutes defaults
        if not dmd.Devices.hasProperty("zRouteMapMaxRoutes"):
            dmd.Devices._setProperty("zRouteMapMaxRoutes", 500, type="int")

zRouteMapMaxRoutesProperty()
