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
import Migrate

class DeviceTemplatesProperty(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zDeviceTemplates"):
            dmd.Devices._setProperty("zDeviceTemplates", ["Device"],
                                     type="lines")

DeviceTemplatesProperty()

