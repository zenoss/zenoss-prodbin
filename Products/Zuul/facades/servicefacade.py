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
from itertools import imap
from zope.interface import implements
from Products.AdvancedQuery import MatchRegexp, And
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.Zuul.facades import TreeFacade
from Products.Zuul.utils import unbrain
from Products.Zuul.interfaces import ITreeFacade, IServiceFacade
from Products.Zuul.interfaces import IServiceOrganizerNode, IInfo, ICatalogTool
from Products.Zuul.infos.service import ServiceOrganizerNode
from Products.Zuul.tree import SearchResults
from Acquisition import aq_base

log = logging.getLogger('zen.ServiceFacade')

class ServiceFacade(TreeFacade):
    implements(IServiceFacade, ITreeFacade)

    @property
    def _classFactory(self):
        return ServiceClass

    @property
    def _classRelationship(self):
        return 'serviceclasses'

    @property
    def _root(self):
        return self._dmd.Services

    @property
    def _instanceClass(self):
        return "Products.ZenModel.Service.Service"

    def _getSecondaryParent(self, obj):
        return obj.serviceclass()

    def getOrganizerTree(self, id):
        obj = self._getObject(id)
        return ServiceOrganizerNode(obj)

    def getParentInfo(self, uid=None):
        obj = self._getObject(uid)
        if isinstance(obj, ServiceClass):
            parent = aq_base(obj.serviceorganizer())
        elif isinstance(obj, ServiceOrganizer):
            parent = aq_base(obj.getParentNode())
        else:
            raise Exception('Illegal type %s' % obj.__class__.__name__)

        info = IInfo(parent)
        return info

    def getList(self, limit=0, start=0, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):
        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'

        qs = []
        query = None
        if params:
            if 'name' in params:
                qs.append(MatchRegexp('name', '(?i).*%s.*' % params['name']))
            if 'port' in params:
                qs.append(MatchRegexp('port', '(?i).*%s.*' % params['port']))
        if qs:
            query = And(*qs)

        brains = cat.search("Products.ZenModel.ServiceClass.ServiceClass",
                            start=start, limit=limit, orderby=sort,
                            reverse=reverse, query=query)

        objs = imap(unbrain, brains)
        infos = imap(IInfo, objs)
        return SearchResults(infos, brains.total, brains.hash_)
