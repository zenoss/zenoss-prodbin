#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ConfmonItem

simple class that non relationship manager items can inherit from
provides the getPrimaryPath and getPrimaryUrlPath functions that are
used throughout the system.


$Id: ConfmonItem.py,v 1.3 2003/10/04 15:54:36 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import urllib

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import getObjByPath

from ConfmonAll import ConfmonAll

class ConfmonItem(ConfmonAll): 
    """Base class for all confmon classes"""

    meta_type = 'ConfmonItem'

    security = ClassSecurityInfo()

    security.declareProtected('View', 'getPrimaryPath')
    def getPrimaryPath(self):
        return self.getPhysicalPath()


    security.declareProtected('View', 'getPrimaryUrlPath')
    def getPrimaryUrlPath(self):
        """get the physicalpath as a url"""
        return urllib.quote('/'.join(self.getPrimaryPath()))

    def aq_primary(self):
        """return this object with is acquisition path set to primary path"""
        return getObjByPath(self.getPhysicalRoot(), self.getPrimaryPath()[1:])

    def primaryAq(self):
        """return this object with is acquisition path set to primary path"""
        return self.aq_primary()


InitializeClass(ConfmonItem)
