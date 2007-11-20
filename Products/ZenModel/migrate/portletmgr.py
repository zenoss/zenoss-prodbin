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
from Products.ZenWidgets.PortletManager import manage_addPortletManager
from Products.ZenWidgets.ZenossPortlets import ZenossPortlets
from Acquisition import aq_base


class PortletManager(Migrate.Step):
    version = Migrate.Version(2, 1, 1)

    def cutover(self, dmd):
        zport = aq_base(dmd.zport)
        if not hasattr(zport, 'ZenPortletManager'):
            manage_addPortletManager(zport)
        zpmgr = zport.ZenPortletManager
        ZenossPortlets.register_default_portlets(zpmgr)

PortletManager()
