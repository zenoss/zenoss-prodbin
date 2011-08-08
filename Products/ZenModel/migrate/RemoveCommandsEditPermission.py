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
__doc__='''
This migration script removes ZEN_DEFINE_COMMANDS_EDIT permission
from the ZenManager role.
''' 

__version__ = "$Revision$"[11:-2]


import Migrate

from Products.ZenModel.ZenossSecurity import *

class RemoveCommandsEditPermission(Migrate.Step):

    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_DEFINE_COMMANDS_EDIT,
            [MANAGER_ROLE], 1)

RemoveCommandsEditPermission()
