#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenModelItem

$Id: ZenModelItem.py,v 1.3 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import urllib

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import getObjByPath

from ZenModelBase import ZenModelBase

class ZenModelItem(ZenModelBase): 
    """
    Simple class that non RelationshipManager items inherit from to
    provide primary path functionality.
    """

    meta_type = 'ZenModelItem'

    security = ClassSecurityInfo()

    security.declareProtected('View', 'getPrimaryPath')
    def getPrimaryPath(self):
        return self.getPhysicalPath()


    security.declareProtected('View', 'getPrimaryUrlPath')
    def getPrimaryUrlPath(self):
        """get the physicalpath as a url"""
        return self.absolute_url_path()


    def primaryAq(self):
        """return this object with is acquisition path set to primary path"""
        return self


InitializeClass(ZenModelItem)
