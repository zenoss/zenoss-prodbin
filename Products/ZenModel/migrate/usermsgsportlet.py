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

import Migrate
from Products.ZenWidgets.ZenossPortlets.ZenossPortlets import \
                                                    register_default_portlets

class UserMsgsPortlet(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()
        zpm = dmd.zport.ZenPortletManager
        register_default_portlets(zpm)

UserMsgsPortlet()
