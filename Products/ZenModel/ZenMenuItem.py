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
    isdialog = False
    banned_classes = () 
    allowed_classes = ()
    ordering = 0.0
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'action', 'type':'text', 'mode':'w'},
        {'id':'isglobal', 'type':'boolean','mode':'w'},
        {'id':'permissions', 'type':'lines', 'mode':'w'},
        {'id':'banned_classes','type':'lines','mode':'w'},
        {'id':'allowed_classes','type':'lines','mode':'w'},
        {'id':'isdialog', 'type':'boolean','mode':'w'},
        {'id':'ordering', 'type':'float','mode':'w'},
        )

    _relations =  (
        ("zenMenus", ToOne(ToManyCont, 'Products.ZenModel.ZenMenu', 'zenMenuItems')),
        )

    security = ClassSecurityInfo()

    def getMenuItemOwner(self):
        parent = self
        for x in range(4):
            parent = parent.getParentNode()
        return parent

    def __cmp__(self, other):
        if other and other.ordering:
            return cmp(self.ordering, other.ordering)
        else:
            return cmp(self.ordering, 0.0)
    
InitializeClass(ZenMenuItem)

