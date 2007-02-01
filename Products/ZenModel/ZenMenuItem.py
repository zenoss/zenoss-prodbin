################################################################################
#
#     Copyright (c) 2007 Zenoss, Inc.
#
################################################################################


from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *

import logging
log = logging.getLogger("zen.Menu")

class ZenMenuItem(ZenModelRM):
    
    meta_type = 'ZenMenuItem'
    security = ClassSecurityInfo()
    description = ""
    action = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'action', 'type':'text', 'mode':'w'},
        )

    zenRelationsBaseModule = 'Products.ZenWidgets'
    _relations =  (
        ("zenMenus", ToManyCont(ToOne, 'ZenMenu', 'zenMenuItems')),
        )

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, id=None, desc='', action='', REQUEST=None):
        """ Add a menu item to a menu """
        mi = None
        if id:
            mu = ZenMenuItem(id)
            self.zenMenuItems._setObject(id, mi)
            if self.meta_type == 'Device':
                self.setLastChange()
            mi.description = desc
            mi.action = action
        if REQUEST:
            if mi:
                REQUEST['message'] = 'Menu Item Added'
                url = '%s/zenMenuItems/%s' % (self.getPrimaryUrlPath(), mi.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return mi

InitializeClass(ZenMenuItem)

