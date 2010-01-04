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

import logging
from zope.interface import implements
from zope.component import queryUtility

from Products.Zuul.interfaces import IFacade, IDataRootFactory, ITreeNode
from Products.Zuul.interfaces import ITreeFacade, IInfo, ICatalogTool
from Products.Zuul.interfaces import IEventInfo
from Products.Zuul.utils import unbrain

log = logging.getLogger('zen.Zuul')

class ZuulFacade(object):
    implements(IFacade)

    @property
    def _dmd(self):
        """
        A way for facades to access the data layer
        """
        dmd_factory = queryUtility(IDataRootFactory)
        if dmd_factory:
            return dmd_factory()


class TreeFacade(ZuulFacade):
    implements(ITreeFacade)

    def getTree(self, uid):
        obj = self._findObject(uid)
        return ITreeNode(obj)

    def getInfo(self, uid=None):
        obj = self._getObject(uid)
        return IInfo(obj)

    def _getObject(self, uid=None):
        if not uid:
            return self._root
        else:
            return self._findObject(uid)

    def _root(self):
        raise NotImplementedError

    def _findObject(self, uid):
        return self._dmd.unrestrictedTraverse(uid)

    def getDevices(self, uid=None):
        cat = ICatalogTool(self._getObject(uid))
        brains = cat.search('Products.ZenModel.Device.Device')
        return map(IInfo, map(unbrain, brains))

    def getEvents(self, uid=None):
        zem = self._dmd.ZenEventManager
        cat = ICatalogTool(self._getObject(uid))
        eventInfos = []
        brains = cat.search(self._instanceClass)
        for instance in map(unbrain, brains):
            try:
                for event in zem.getEventListME(instance):
                    if not getattr(event, 'device', None):
                        event.device = instance.device().id
                    if not getattr(event, 'component', None):
                        event.component = instance.name()
                    eventInfos.append(IEventInfo(event))
            except Exception:
                msg = "Failed to get event list for process '%s'"
                args = (instance.titleOrId(),)
                log.error(msg, *args)
                continue
        return eventInfos



from eventfacade import EventFacade
from processfacade import ProcessFacade
from servicefacade import ServiceFacade
