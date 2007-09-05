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

class ZenManagerRole(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        zport = dmd.zport
        zport.__ac_roles__ += ('ZenManager',)
        rm = dmd.getPhysicalRoot().acl_users.roleManager
        if "ZenManager" in rm.listRoleIds(): return
        rm.addRole("ZenManager")
        mp = zport.manage_permission
        mp('Delete objects', ['ZenManager', 'Owner','Manager',],     1)
        mp('Add DMD Objects', ['ZenManager', 'Owner','Manager',],     1)
        mp('View',['ZenUser','ZenManager','Manager','Owner'])
        mp('View History',['ZenUser', 'ZenManager', 'Manager',], 1)
        mp(ZEN_COMMON,['ZenUser','ZenManager','Manager', 'Owner'], 1)


ZenManagerRole()
