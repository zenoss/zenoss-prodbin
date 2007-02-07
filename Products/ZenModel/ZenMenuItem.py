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
    permissions = (Permissions.view,)
    isglobal = True
    banned_classes = ()
    allowed_classes = ()
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'action', 'type':'text', 'mode':'w'},
        {'id':'isglobal', 'type':'boolean','mode':'w'},
        {'id':'permissions', 'type':'lines', 'mode':'w'},
        )

    _relations =  (
        ("zenMenus", ToOne(ToManyCont, 'ZenMenu', 'zenMenuItems')),
        )

    security = ClassSecurityInfo()

    def getMenuItemOwner(self):
        parent = self
        for x in range(4):
            parent = parent.getParentNode()
        return parent

InitializeClass(ZenMenuItem)

