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
from Products.ZenWidgets.ZenossPortlets.ZenossPortlets import portlets

class PortletPaths(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        zpm = dmd.zport.ZenPortletManager
        for portlet in portlets:
            pobj = zpm.find(portlet['id'])
            if pobj: pobj.sourcepath = portlet['sourcepath']

PortletPaths()
