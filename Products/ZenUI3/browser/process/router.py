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

from Products.ZenUtils.Ext import DirectRouter
from Products import Zuul

# these imports will go away once every method is converted to the new way
# like getInfo/setInfo
import zope.component
from Products.Zuul.interfaces import ISerializableFactory, IProcessFacade

class ProcessRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('process')

    def getTree(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        tree = facade.getTree(id)
        factory = ISerializableFactory(tree)
        serializableTree = factory()
        return serializableTree['children']

    def getInfo(self, id, keys=None):
        facade = self._getFacade()
        process = facade.getInfo(id)
        data = Zuul.marshal(process, keys)
        return {'data': data, 'success': True}

    def setInfo(self, **data):
        facade = self._getFacade()
        process = facade.getInfo(data['id'])
        Zuul.unmarshal(data, process)
        return {'success': True}

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

    def getEvents(self, id):
        facade = zope.component.queryUtility(IProcessFacade)
        events = facade.getEvents(id)
        serializableEvents = []
        for event in events:
            factory = ISerializableFactory(event)
            serializableEvents.append(factory())
        return {'data': serializableEvents,
                'success': True}
