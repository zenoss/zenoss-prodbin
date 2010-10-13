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

from zope.component import provideHandler
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer

Device = 'Products.ZenModel.Device.Device'
DeviceComponent = 'Products.ZenModel.DeviceComponent.DeviceComponent'

class CreateGUIDsForDeviceAndComponent(Migrate.Step):
    version = Migrate.Version(3, 1, 0)
    def __init__(self):
        Migrate.Step.__init__(self)

    def cutover(self, dmd):
        if getattr(dmd, 'guid_table', None) is None:
            for b in ICatalogTool(dmd).search((Device, DeviceComponent, 
                                               DeviceOrganizer)):
                IGlobalIdentifier(b.getObject()).create(force=True)

CreateGUIDsForDeviceAndComponent()
