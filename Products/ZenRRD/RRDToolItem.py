#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM


class RRDToolItem(ZenModelRM):
    """base class for RRDTool persistent classes"""


    security = ClassSecurityInfo()

    zenRelationsBaseModule = "Products.ZenRRD"
    
    def getName(self):
        """Return the name of this item (take off the type from the id).
        """
        return self.id


InitializeClass(RRDToolItem)
