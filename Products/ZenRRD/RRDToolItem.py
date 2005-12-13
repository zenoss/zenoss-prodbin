#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RenderServer

Frontend that passes rrd graph options to rrdtool to render.  

$Id: RRDToolItem.py,v 1.1 2003/04/04 16:28:07 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Acquisition import Implicit
from Globals import Persistent
from AccessControl.Role import RoleManager
from OFS.SimpleItem import Item

import utils

class RRDToolItem(Implicit, Persistent, RoleManager, Item):
    """base class for RRDTool persistent classes"""

    manage_options = (Item.manage_options + RoleManager.manage_options)

    def getName(self):
        """Return the name of this item (take off the type from the id).
        """
        return utils.rootid(self.meta_type + '-', self.id)
