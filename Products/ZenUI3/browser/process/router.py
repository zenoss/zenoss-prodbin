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

from Products.Zuul.interfaces import ISerializableFactory, IProcessFacade
from Products.ZenUtils.Ext import DirectRouter

class ProcessRouter(DirectRouter):
    
    def loadProcessTree(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        tree = facade.getProcessTree(id)
        factory = ISerializableFactory(tree)
        serializableTree = factory()
        return serializableTree['children']
        
    def loadProcessInfo(self, processTreeId):
        facade = zope.component.queryUtility(IProcessFacade)
        info = facade.getProcessInfo(processTreeId)
        factory = ISerializableFactory(info)
        serializableInfo = factory()
        return {'data': serializableInfo,
                'success': True
                }
                
