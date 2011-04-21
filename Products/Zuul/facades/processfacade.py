###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from itertools import izip, count, imap
from zope.event import notify
from Acquisition import aq_parent
from zope.interface import implements
from Products.AdvancedQuery import MatchRegexp, And
from Products.ZenModel.OSProcess import OSProcess
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IProcessFacade, ITreeFacade
from Products.Zuul.utils import unbrain
from Products.Zuul.interfaces import IInfo, ICatalogTool
from Products.Zuul.tree import SearchResults
from zope.app.container.contained import ObjectMovedEvent

log = logging.getLogger('zen.ProcessFacade')


class ProcessFacade(TreeFacade):
    implements(IProcessFacade, ITreeFacade)

    @property
    def _root(self):
        return self._dmd.Processes

    def _classFactory(self, contextUid):
        return OSProcessClass

    @property
    def _classRelationship(self):
        return 'osProcessClasses'

    @property
    def _instanceClass(self):
        return "Products.ZenModel.OSProcess.OSProcess"

    def _getSecondaryParent(self, obj):
        return obj.osProcessClass()

    def moveProcess(self, uid, targetUid):
        obj = self._getObject(uid)
        target = self._getObject(targetUid)
        brainsCollection = []

        # reindex all the devices and processes underneath this guy and the target
        for org in (obj.getPrimaryParent().getPrimaryParent(), target):
            catalog = ICatalogTool(org)
            brainsCollection.append(catalog.search(OSProcess))

        if isinstance(obj, OSProcessClass):
            source = obj.osProcessOrganizer()
            source.moveOSProcessClasses(targetUid, obj.id)
            newObj = getattr(target.osProcessClasses, obj.id)
        elif isinstance(obj, OSProcessOrganizer):
            source = aq_parent(obj)
            source.moveOrganizer(targetUid, (obj.id,))
            newObj = getattr(target, obj.id)
        else:
            raise Exception('Illegal type %s' % obj.__class__.__name__)

        # fire the object moved event for the process instances (will update catalog)
        for brains in brainsCollection:
            objs = imap(unbrain, brains)
            for item in objs:
                notify(ObjectMovedEvent(item, item.os(), item.id, item.os(), item.id))


        return newObj.getPrimaryPath()

    def getSequence(self):
        processClasses = self._dmd.Processes.getSubOSProcessClassesSorted()
        for processClass in processClasses:
            yield {
                'uid': '/'.join(processClass.getPrimaryPath()),
                'folder': processClass.getPrimaryParent().getOrganizerName(),
                'name': processClass.name,
                'regex': processClass.regex,
                'monitor': processClass.zMonitor,
                'count': processClass.count()
            }

    def setSequence(self, uids):
        for sequence, uid in izip(count(), uids):
            ob = self._getObject(uid)
            ob.sequence = sequence

    def _processSearch(self, limit=None, start=None, sort='name', dir='ASC',
              params=None, uid=None, criteria=()):
        cat = ICatalogTool(self._getObject(uid))

        # Prime the cache
        if start==0:
            cat.count('Products.ZenModel.OSProcess.OSProcess', uid)

        reverse = dir=='DESC'
        qs = []
        query = None
        if params:
            if 'name' in params:
                qs.append(MatchRegexp('name', '(?i).*%s.*' % params['name']))
        if qs:
            query = And(*qs)

        return cat.search("Products.ZenModel.OSProcessClass.OSProcessClass",
                          start=start, limit=limit, orderby=sort,
                          reverse=reverse, query=query)

    def getList(self, limit=None, start=None, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):
        brains = self._processSearch(limit, start, sort, dir, params, uid, criteria)
        wrapped = imap(IInfo, imap(unbrain, brains))
        return SearchResults(wrapped, brains.total, brains.hash_)

