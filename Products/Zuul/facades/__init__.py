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
from Acquisition import aq_base, aq_parent
from zope.interface import implements
from zope.component import queryUtility, adapts

from Products.AdvancedQuery import MatchRegexp, And, Generic, Or, Eq, Between
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.interfaces import IFacade, IDataRootFactory, ITreeNode
from Products.Zuul.interfaces import ITreeFacade, IInfo, ICatalogTool
from Products.Zuul.interfaces import IEventInfo
from Products.Zuul.utils import unbrain
from Products.ZenUtils.IpUtil import numbip, checkip, IpAddressError
from Products.ZenUtils.IpUtil import getSubnetBounds

log = logging.getLogger('zen.Zuul')


class InfoBase(object):
    implements(IInfo)
    adapts(ZenModelRM)

    def __init__(self, object):
        self._object = object

    @property
    def uid(self):
        _uid = getattr(self, '_v_uid', None)
        if _uid is None:
            _uid = self._v_uid = '/'.join(self._object.getPrimaryPath())
        return _uid

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
        try:
            return self._dmd.unrestrictedTraverse(uid)
        except Exception:
            logging.error('Could not find object "%s"' % uid)
            raise

    def deviceCount(self, uid=None):
        cat = ICatalogTool(self._getObject(uid))
        return cat.count('Products.ZenModel.Device.Device')

    def getDevices(self, uid=None, start=0, limit=50, sort='name', dir='ASC',
                   params=None):
        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'
        qs = []
        query = None
        if params:
            if 'name' in params:
                qs.append(MatchRegexp('name', '(?i).*%s.*' % params['name']))
            if 'ipAddress' in params:
                ip = params['ipAddress']
                try:
                    checkip(ip)
                except IpAddressError:
                    pass
                else:
                    if numbip(ip):
                        minip, maxip = getSubnetBounds(ip)
                        qs.append(Between('ipAddress', str(minip), str(maxip)))
            if 'deviceClass' in params:
                qs.append(MatchRegexp('uid', '(?i).*%s.*' %
                                      params['deviceClass']))
            if 'productionState' in params:
                qs.append(Or(*[Eq('productionState', str(state))
                             for state in params['productionState']]))
        if qs:
            query = And(*qs)
        brains = cat.search('Products.ZenModel.Device.Device', start=start,
                           limit=limit, orderby=sort, reverse=reverse,
                            query=query)
        return map(IInfo, map(unbrain, brains))

    def getInstances(self, uid=None, start=0, limit=50, sort='name',
                     dir='ASC', params=None):
        # do the catalog search
        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'
        brains = cat.search(self._instanceClass, start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        objs = imap(unbrain, brains)
        # the objects returned by the catalog search are wrapped in the
        # acquisition context of their primary path. Switch these objects
        # to the context of the parent indentified by the uid parameter.
        secondaryParent = self._dmd.unrestrictedTraverse(uid)
        context = secondaryParent.instances
        def switchContext(obj):
            return aq_base(obj).__of__(context)
        instances = imap(switchContext, objs)
        # convert to info objects
        return imap(IInfo, instances)

    def _parameterizedWhere(self, uid=None):
        cat = ICatalogTool(self._dmd)
        brains = cat.search(self._instanceClass, paths=(uid,))
        criteria = []
        for instance in brains:
            component = instance.id
            path = instance.getPath().split('/')
            device = path[path.index('devices') + 1]
            criteria.append(dict(device=device, component=component))

        # Build parameterizedWhere
        where = []
        vals = []
        for criterion in criteria:
            s = []
            # criterion is a dict
            for k, v in criterion.iteritems():
                s.append('%s=%%s' % k)
                vals.append(v)
            crit = ' and '.join(s)
            where.append('(%s)' % crit)
        if where:
            crit = ' or '.join(where)
            parameterizedWhere = ('(%s)' % crit, vals)
        else:
            parameterizedWhere = None
        return parameterizedWhere

    def getEvents(self, uid=None):
        zem = self._dmd.ZenEventManager
        events = zem.getEventList(
            parameterizedWhere=self._parameterizedWhere(uid))
        # return IInfos
        for e in imap(IEventInfo, events):
            yield e

    def getEventSummary(self, uid=None):
        zem = self._dmd.ZenEventManager
        where = self._parameterizedWhere(uid)
        summary = zem.getEventSummary(parameterizedWhere=where)
        severities = (c[0].lower() for c in zem.severityConversions)
        counts = (s[1]+s[2] for s in summary)
        return zip(severities, counts)

    def addOrganizer(self, contextUid, id):
        context = self._findObject(contextUid)
        organizer = aq_base(context).__class__(id)
        context._setObject(id, organizer)
        return '%s/%s' % (contextUid, id)

    def addClass(self, contextUid, id):
        context = self._findObject(contextUid)
        _class = self._classFactory(id)
        relationship = getattr(context, self._classRelationship)
        relationship._setObject(id, _class)
        return '%s/%s/%s' % (contextUid, self._classRelationship, id)

    def deleteNode(self, uid):
        obj = self._findObject(uid)
        context = aq_parent(obj)
        context._delObject(obj.id)

from eventfacade import EventFacade
from processfacade import ProcessFacade
from servicefacade import ServiceFacade
from devicefacade import DeviceFacade
