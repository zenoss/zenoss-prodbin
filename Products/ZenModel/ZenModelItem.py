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


    def __init__(self, id):
        self.id = id


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
