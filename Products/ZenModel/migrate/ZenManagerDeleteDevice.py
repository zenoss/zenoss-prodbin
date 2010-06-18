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
__doc__="""
Add permission for deleting devices to the ZenManager role.
"""

import Migrate
from Products.ZenModel.ZenossSecurity import *

class ZenManagerDeleteDevice(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_DELETE_DEVICE,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)

ZenManagerDeleteDevice()
