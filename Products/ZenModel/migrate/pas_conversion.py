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
from Products.ZenUtils import addLoginForm

import Migrate

class MigrateToPAS(Migrate.Step):
    version = 24.0

    def cutover(self, dmd):
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            migratePAS(context)
            # note that the addLoginForm() is not PAS-native; it's part of a
            # monkey patch we have applied to allow for a file-system-based
            # login page template. See ZenUtils.__init__ and ZenUtils.Security.
            context.acl_users.cookieAuthHelper.addLoginForm()
MigrateToPAS()

