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
__doc__="""
WinServiceClass is now a subclass of ServiceClass. We need to iterate over
all of the appropriate ServiceClasses in the system and convert them.
"""

import Migrate
from Products.ZenModel.WinServiceClass import WinServiceClass, STARTMODE_AUTO
from Products.ZenModel.ServiceClass import ServiceClass


class AddWinServiceClass(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for service_class in dmd.Services.WinService.getSubClassesGen():
            if service_class.__class__ == ServiceClass:
                service_class.__class__ = WinServiceClass
                service_class.monitoredStartModes = [STARTMODE_AUTO]


AddWinServiceClass()
