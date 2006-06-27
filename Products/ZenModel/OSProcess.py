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

    procName = ""
    parameters = ""
    _procKey = ""

    _properties = OSComponent._properties + (
        {'id':'procName', 'type':'string', 'mode':'w'},
        {'id':'parameters', 'type':'string', 'mode':'w'},
        {'id':'zCountProcs', 'type':'boolean', 'mode':'w'},
        {'id':'zAlertOnRestarts', 'type':'boolean', 'mode':'w'},
    )

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "processes")),
        ("osProcessClass", ToOne(ToMany, "OSProcessClass", "instances")),
    )

    security = ClassSecurityInfo()

    def setOSProcessClass(self, procKey):
        """Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        self._procKey = self.getDmdRoot("Processes").setOSProcessClass(
                                self, procKey)
        return self._procKey
    

    def getOSProcessClass(self):
        """Return the current procKey.
        """
        return self._procKey
        
    
    def name(self):
        return self.procName


InitializeClass(OSProcess)
