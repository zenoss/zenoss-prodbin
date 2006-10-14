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

from Products.ZenUtils.Security import refreshLoginForm
from Products.ZenUtils.Security import replaceACLWithPAS

import Migrate

class MigrateToPAS(Migrate.Step):
    version = 23.0


    def cutover(self, dmd):
        newModule = 'Products.PluggableAuthService.PluggableAuthService'
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            if context.acl_users.__module__ != newModule:
                replaceACLWithPAS(context)
            refreshLoginForm(context.acl_users)

MigrateToPAS()

