###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """
Denormalizes serviceName and caption WinService properties to avoid loading
entire service class objects for common operations.
"""
import Migrate


class AddWinServiceProperties(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for b in dmd.Devices.componentSearch(meta_type='WinService'):
            service = b.getObject()
            serviceClass = service.serviceclass()
            if serviceClass:
                service.serviceName = serviceClass.name
                service.caption = serviceClass.description


AddWinServiceProperties()
