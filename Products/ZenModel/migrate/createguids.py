###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

Device = 'Products.ZenModel.Device.Device'
DeviceComponent = 'Products.ZenModel.DeviceComponent.DeviceComponent'

class CreateGUIDsForDeviceAndComponent(Migrate.Step):
    version = Migrate.Version(3, 1, 0)

    def cutover(self, dmd):
        if getattr(dmd, 'guid_table', None) is None:
            for b in ICatalogTool(dmd).search((Device, DeviceComponent)):
                IGlobalIdentifier(b.getObject()).create()

CreateGUIDsForDeviceAndComponent()
