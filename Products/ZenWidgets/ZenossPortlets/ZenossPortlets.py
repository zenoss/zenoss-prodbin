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

import os
from Products.ZenModel.ZenossSecurity import *

def _portletpath(*args):
    """
    Shortcut, since these all live in the same directory. Portlet needs a path
    relative to $ZENHOME.
    """
    return os.path.join('Products','ZenWidgets','ZenossPortlets', *args)

portlets = [
    {
     'sourcepath':  _portletpath('HeartbeatsPortlet.js'), 
     'id':          'HeartbeatsPortlet', 
     'title': 'Zenoss Issues',
     'permission':  ZEN_MANAGE_DMD
    },
    {
     'sourcepath':  _portletpath('GoogleMapsPortlet.js'), 
     'id':          'GoogleMapsPortlet', 
     'title': 'Google Maps',
     'permission':  ZEN_VIEW
    },
    {
     'sourcepath':  _portletpath('DeviceIssuesPortlet.js'), 
     'id':          'DeviceIssuesPortlet', 
     'title': 'Device Issues',
     'permission':  ZEN_COMMON
    },
    {
     'sourcepath':  _portletpath('TopLevelOrgsPortlet.js'), 
     'id':          'TopLevelOrgsPortlet', 
     'title': 'Top Level Organizers',
     'permission':  ZEN_VIEW
    },
    {
     'sourcepath':  _portletpath('WatchListPortlet.js'), 
     'id':          'WatchListPortlet', 
     'title': 'Watch List',
     'permission':  ZEN_COMMON
    },
    {
     'sourcepath':  _portletpath('productionStatePortlet.js'), 
     'id':          'ProdStatePortlet', 
     'title': 'Production States',
     'permission':  ZEN_COMMON
    },
]

def register_default_portlets(portletmanager):
    for portlet in portlets:
        portletmanager.register_portlet(**portlet)


