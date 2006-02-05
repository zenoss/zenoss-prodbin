#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

class OSProcess(OSComponent):
    """Hardware object"""
    portal_type = meta_type = 'OSProcess'

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "processes")),
    )

    security = ClassSecurityInfo()

InitializeClass(OSProcess)
