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
import os
from Products.ZenWidgets.PortletManager import manage_addPortletManager
from Products.ZenModel.ZenossSecurity import ZEN_VIEW, ZEN_COMMON
from Acquisition import aq_base

def portletpath(*args):
    workdir = os.environ['ZENHOME']+ '/Products/ZenWidgets'
    return os.path.join(workdir, *args)

portlets = [
    {
     'sourcepath':  portletpath('ZenossPortlets/HeartbeatsPortlet.js'), 
     'id':          'HeartbeatsPortlet', 
     'title': 'Zenoss Issues',
     'permission':  ZEN_VIEW
    },
    {
     'sourcepath':  portletpath('ZenossPortlets/GoogleMapsPortlet.js'), 
     'id':          'GoogleMapsPortlet', 
     'title': 'Google Maps',
     'permission':  ZEN_VIEW
    },
    {
     'sourcepath':  portletpath('ZenossPortlets/DeviceIssuesPortlet.js'), 
     'id':          'DeviceIssuesPortlet', 
     'title': 'Device Issues',
     'permission':  ZEN_COMMON
    },
    {
     'sourcepath':  portletpath('ZenossPortlets/TopLevelOrgsPortlet.js'), 
     'id':          'TopLevelOrgsPortlet', 
     'title': 'Top Level Organizers',
     'permission':  ZEN_VIEW
    },
    {
     'sourcepath':  portletpath('ZenossPortlets/WatchListPortlet.js'), 
     'id':          'WatchListPortlet', 
     'title': 'Watch List',
     'permission':  ZEN_COMMON
    },
    {
     'sourcepath':  portletpath('ZenossPortlets/productionStatePortlet.js'), 
     'id':          'ProdStatePortlet', 
     'title': 'Production States',
     'permission':  ZEN_COMMON
    },
]


class PortletManager(Migrate.Step):
    version = Migrate.Version(2, 1, 1)

    def cutover(self, dmd):
        zport = aq_base(dmd.zport)
        if not hasattr(zport, 'ZenPortletManager'):
            manage_addPortletManager(zport)
        zpmgr = zport.ZenPortletManager
        for portlet in portlets:
            zpmgr.register_portlet(**portlet)

PortletManager()
