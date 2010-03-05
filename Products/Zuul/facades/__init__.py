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

"""
Zuul facades are part of the Python API.  The main functions of facades are
(1) given a unique identified (UID) retrieve a ZenModel object and return info
objects representing objects related to the retrieved object, and (2) given an
info object bind its properties to a ZenModel object and save it. The UID is
typically an acquisition path, e.g. '/zport/dmd/Devices'. Facades use an
ICatalogTool to search for the ZenModel object using the UID.

Documentation for the classes and methods in this module can be found in the
definition of the interface that they implement.
"""

import logging
from itertools import imap
from Acquisition import aq_base, aq_parent
from OFS.ObjectManager import checkValidId
from zope.interface import implements
from zope.component import queryUtility

from Products.AdvancedQuery import MatchRegexp, And, Or, Eq, Between
from Products.Zuul.interfaces import IFacade, IDataRootFactory, ITreeNode
from Products.Zuul.interfaces import ITreeFacade, IInfo, ICatalogTool
from Products.Zuul.interfaces import IEventInfo
from Products.Zuul.utils import unbrain
from Products.Zuul.tree import SearchResults
from Products.ZenUtils.IpUtil import numbip, checkip, IpAddressError, ensureIp
from Products.ZenUtils.IpUtil import getSubnetBounds

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

    def _getObject(self, uid):
        try:
            obj = self._dmd.unrestrictedTraverse(str(uid))
        except Exception, e:
            args = (uid, e.__class__.__name__, e)
            raise Exception('Cannot find "%s". %s: %s' % args)
        return obj


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
        return super(TreeFacade, self)._getObject(uid)

    def _root(self):
        raise NotImplementedError

    def deviceCount(self, uid=None):
        cat = ICatalogTool(self._getObject(uid))
        return cat.count('Products.ZenModel.Device.Device')

    def getDevices(self, uid=None, start=0, limit=50, sort='name', dir='ASC',
                   params=None, hashcheck=None):
        cat = ICatalogTool(self._getObject(uid))
        reverse = dir=='DESC'
        qs = []
        query = None
        if params:
            if 'name' in params:
                qs.append(MatchRegexp('name', '(?i).*%s.*' % params['name']))
            if 'ipAddress' in params:
                ip = ensureIp(params['ipAddress'])
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
                            query=query, hashcheck=hashcheck)

        wrapped = imap(IInfo, imap(unbrain, brains))
        return SearchResults(wrapped, brains.total, brains.hash_)

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
        def switchContext(obj):
            parent = self._getSecondaryParent(obj)
            parent = aq_base(parent).__of__(parent.getPrimaryParent())

            return aq_base(obj).__of__(parent.instances)
        instances = imap(switchContext, objs)
        # convert to info objects
        return SearchResults(imap(IInfo, instances), brains.total,
                             brains.hash_)

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
        context = self._getObject(contextUid)
        organizer = aq_base(context).__class__(id)
        context._setObject(id, organizer)
        return '%s/%s' % (contextUid, id)

    def addClass(self, contextUid, id):
        context = self._getObject(contextUid)
        _class = self._classFactory(id)
        relationship = getattr(context, self._classRelationship)
        checkValidId(relationship, id)
        relationship._setObject(id, _class)
        return '%s/%s/%s' % (contextUid, self._classRelationship, id)

    def deleteNode(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        context._delObject(obj.id)

from eventfacade import EventFacade
from processfacade import ProcessFacade
from servicefacade import ServiceFacade
from devicefacade import DeviceFacade
from templatefacade import TemplateFacade
from zenpackfacade import ZenPackFacade
