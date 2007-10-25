import os
from Products.ZenModel.ZenossSecurity import *

def portletpath(*args):
    workdir = os.environ['ZENHOME']+ '/Products/ZenWidgets'
    return os.path.join(workdir, *args)

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


