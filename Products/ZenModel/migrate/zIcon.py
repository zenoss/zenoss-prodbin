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

Add zLinks to DeviceClass.

'''
import Migrate

class zIconProperty(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        if not dmd.Networks.hasProperty('zIcon'):
            dmd.Networks._setProperty(
                "zIcon", "/zport/dmd/img/icons/network.png")
        if not dmd.Devices.hasProperty('zIcon'):
            dmd.Devices._setProperty(
                "zIcon", "/zport/dmd/img/icons/noicon.png")
        if not dmd.Devices.Network.Router.hasProperty('zIcon'):
            dmd.Devices.Network.Router._setProperty(
                "zIcon", "/zport/dmd/img/icons/router.png")
        if not dmd.Devices.Server.hasProperty('zIcon'):
            dmd.Devices.Server._setProperty(
                "zIcon", "/zport/dmd/img/icons/server.png")


zIconProperty()


