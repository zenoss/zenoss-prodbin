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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM


class RRDToolItem(ZenModelRM):
    """base class for RRDTool persistent classes"""


    security = ClassSecurityInfo()
    
    def getName(self):
        """Return the name of this item (take off the type from the id).
        """
        return self.id


InitializeClass(RRDToolItem)
