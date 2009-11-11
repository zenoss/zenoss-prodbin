###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import zope.component

from Products.Zuul.interfaces import IProcessService
from Products.ZenUtils.Ext import DirectRouter

class ProcessRouter(DirectRouter):
    
    def getProcessTree(self, id):
        svc = zope.component.queryUtility(IProcessService)
        tree = svc.getProcessTree(id)
        return tree.serializableObject['children']
        
