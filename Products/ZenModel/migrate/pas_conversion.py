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
This migration script converts Zenoss instances from using old-style,
non-pluggable acl_users "User Folders" to an acl_users based on the
"PluggableAuthenticationService."

Old users, passwords and roles are migrated to PAS with this script.
''' 

__version__ = "$Revision$"[11:-2]

from Products.ZenUtils.Security import migratePAS

import Migrate

class MigrateToPAS(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            migratePAS(context)
MigrateToPAS()

