##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""__init__

Initializer for ZenTableManager

$Id: __init__.py,v 1.3 2004/04/04 23:56:49 edahl Exp $"""

__version__ = 0.5
__revision__ = "$Revision: 1.3 $"[11:-2]


from Products.Five.browser import BrowserView
from ZenTableManager import ZenTableManager
from ZenTableManager import manage_addZenTableManager

try:
    from Products.CMFCore.DirectoryView import registerDirectory
    registerDirectory('skins', globals())
except ImportError: pass

from ZenossPortlets.ZenossPortlets import register_default_portlets

def update_portlets(app):
    """
    Reread in portlet source on startup. If this is the initial load, and
    objects don't exist yet, don't do anything.
    """
    if hasattr(app, 'zport') and hasattr(app.zport, 'ZenPortletManager'):
        register_default_portlets(app.zport.ZenPortletManager)
        for pack in app.zport.dmd.ZenPackManager.packs():
            for portlet in getattr(pack, 'register_portlets', lambda *x:())():
                if app.zport.ZenPortletManager.find(portlet['id']) is None:
                    app.zport.ZenPortletManager.register_extjsPortlet(**portlet)

def initialize(registrar):
    registrar.registerClass(
        ZenTableManager,
        permission="Add ZenTableManager",
        constructors = (manage_addZenTableManager,),
        icon = "ZenTableManager_icon.gif"
    )

def registerPortlets(event):
    """
    Handler for IZopeApplicationOpenedEvent which registers portlets.
    """
    update_portlets(event.app)

# Enable gzip compression of static files
import FileGzipper
if 0:
    FileGzipper = None                  # pyflakes

class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++extjs')[name]
