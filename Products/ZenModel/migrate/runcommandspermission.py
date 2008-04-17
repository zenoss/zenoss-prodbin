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
This migration script adds the ZenManager role.
''' 

__version__ = "$Revision$"[11:-2]


import Migrate

from Products.ZenModel.ZenossSecurity import *

class RunCommandsPermission(Migrate.Step):

    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_RUN_COMMANDS, 
                        [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        

RunCommandsPermission()
