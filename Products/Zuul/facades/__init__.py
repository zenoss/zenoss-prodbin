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
from zope.component import queryUtility, adapts

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.interfaces import IFacade, IDataRootFactory, ITreeNode
from Products.Zuul.interfaces import ITreeFacade, IInfo, ICatalogTool
from Products.Zuul.interfaces import IEventInfo
from Products.Zuul.utils import unbrain
from Products.Zuul.decorators import memoize

log = logging.getLogger('zen.Zuul')


class InfoBase(object):
    implements(IInfo)
    adapts(ZenModelRM)

    def __init__(self, object):
        self._object = object

    @property
    @memoize
    def uid(self):
        return '/'.join(self._object.getPrimaryPath())

    @property
    def id(self):
        return self._object.id

    def getName(self):
        return self._object.titleOrId()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    def getDescription(self):
        return self._object.description

    def setDescription(self, value):
        self._object.description = value

    description = property(getDescription, setDescription) 

    def __repr__(self):
        return '<%s Info "%s">' % (self._object.__class__.__name__, self.id)



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

    def getTree(self, uid=None):
        obj = self._getObject(uid)
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

    def deviceCount(self, uid=None):
        cat = ICatalogTool(self._getObject(uid))
        return cat.count('Products.ZenModel.Device.Device')

    def getDevices(self, uid=None, start=0, limit=50, sort='name', dir='ASC',
                   params=None):
        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'
        brains = cat.search('Products.ZenModel.Device.Device', start=start,
                           limit=limit, orderby=sort, reverse=reverse)
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
from devicefacade import DeviceFacade
