##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Acquisition import aq_parent
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenRelations.RelSchema import *

import logging
log = logging.getLogger("zen.Menu")

class ZenMenuItem(ZenModelRM, ZenPackable):
    
    meta_type = 'ZenMenuItem'
    security = ClassSecurityInfo()
    description = ""
    action = ""
    permissions = (Permissions.view,)
    isglobal = True
    isdialog = False
    banned_classes = () 
    allowed_classes = ()
    banned_ids = () 
    ordering = 0.0

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'action', 'type':'text', 'mode':'w'},
        {'id':'isglobal', 'type':'boolean','mode':'w'},
        {'id':'permissions', 'type':'lines', 'mode':'w'},
        {'id':'banned_classes','type':'lines','mode':'w'},
        {'id':'allowed_classes','type':'lines','mode':'w'},
        {'id':'banned_ids','type':'lines','mode':'w'},
        {'id':'isdialog', 'type':'boolean','mode':'w'},
        {'id':'ordering', 'type':'float','mode':'w'},
        )

    _relations =  (
        ("zenMenus", ToOne(ToManyCont, 'Products.ZenModel.ZenMenu', 'zenMenuItems')),
        ) + ZenPackable._relations

    security = ClassSecurityInfo()

    def getMenuItemOwner(self):
        parent = self.primaryAq()
        for unused in range(4):
            parent = aq_parent(parent)
        return parent

    def __cmp__(self, other):
        if isinstance(other, ZenMenuItem):
            if other and other.ordering:
                return cmp(other.ordering, self.ordering)
            else:
                return cmp(0.0, self.ordering)
        return cmp(id(self), id(other))
    
InitializeClass(ZenMenuItem)
