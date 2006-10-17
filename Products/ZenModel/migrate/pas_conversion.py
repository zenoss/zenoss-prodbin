#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
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
    version = 23.0

    def cutover(self, dmd):
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            migratePAS(context)

MigrateToPAS()

