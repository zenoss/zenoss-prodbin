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

from Products.ZenModel.ZenossSecurity import *
from Products.ZenUtils.Utils import zenPath

def portletpath(*args):
    return zenPath('/Products/ZenWidgets', *args)

portlets = [
    {
     'sourcepath':  portletpath('ZenossPortlets/HeartbeatsPortlet.js'), 
     'id':          'HeartbeatsPortlet', 
     'title': 'Zenoss Issues',
     'permission':  ZEN_MANAGE_DMD
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

def register_default_portlets(portletmanager):
    for portlet in portlets:
        portletmanager.register_portlet(**portlet)


