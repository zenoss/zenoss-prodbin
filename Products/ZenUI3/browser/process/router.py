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

    def getProcessTree(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        tree = facade.getTree(id)
        factory = ISerializableFactory(tree)
        serializableTree = factory()
        return serializableTree['children']

    def getProcessInfo(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        info = facade.getInfo(id)
        factory = ISerializableFactory(info)
        serializableInfo = factory()
        return {'data': serializableInfo,
                'success': True
                }

    def getMonitoringInfo(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        info = facade.getMonitoringInfo(id)
        factory = ISerializableFactory(info)
        serializableInfo = factory()
        return {'data': serializableInfo,
                'success': True
                }

    def getDevices(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        infos = facade.getDevices(id)
        serializableInfos = []
        for info in infos:
            factory = ISerializableFactory(info)
            serializableInfos.append(factory())
        return {'data': serializableInfos,
                'success': True
                }
