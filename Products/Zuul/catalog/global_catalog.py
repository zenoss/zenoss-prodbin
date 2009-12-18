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

import time
from zope.interface import providedBy, ro, implements, classImplementsOnly
from zope.interface import implementedBy
from zope.component import adapts
from AccessControl import getSecurityManager
from AccessControl.PermissionRole import rolesForPermissionOn
from Products.CMFCore.utils import _mergedLocalRoles
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZenUtils.Search import makeMultiPathIndex
from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseSensitiveKeywordIndex
from Products.ZenWidgets.Portlet import Portlet
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.Device import Device

from interfaces import IGloballyIndexed, IPathReporter, IIndexableWrapper


def _allowedRoles(user):
    roles = list(user.getRoles())
    roles.append('Anonymous')
    roles.append('user:%s' % user.getId())
    return roles


class IndexableWrapper(object):
    implements(IIndexableWrapper)
    adapts(IGloballyIndexed)

    def __init__(self, context):
        self._context = context

    def __getattr__(self, name):
        return getattr(self._context, name)

    def allowedRolesAndUsers(self):
        """
        Roles and users with View permission.

        This is a KeywordIndex on the catalog.
        """
        allowed = set()
        for r in rolesForPermissionOn("View", self._context):
            allowed.add(r)
        for user, roles in _mergedLocalRoles(self._context).iteritems():
            for role in roles:
                if role in allowed:
                    allowed.add('user:' + user)
        if 'Owner' in allowed:
            allowed.remove('Owner')
        return list(allowed)

    def objectImplements(self):
        """
        All interfaces and classes implemented by an object.

        This is a KeywordIndex on the catalog.
        """
        dottednames = set()
        # Add all interfaces provided by object
        for iface in providedBy(self._context).flattened():
            dottednames.add(iface.__identifier__)
        # Add the highest five classes in resolution order. 5 is
        # an arbitrary number; essentially, we only care about indexing
        # Zenoss classes, and our inheritance tree isn't that deep. Past
        # 5 we index a bunch of ObjectManager, Persistent, etc., which
        # we'll never use, and enact a significant performance penalty
        # when inserting keywords into the index.
        for kls in ro.ro(self._context.__class__)[:5]:
            dottednames.add('%s.%s' % (kls.__module__, kls.__name__))
        return list(dottednames)

    def path(self):
        """
        Paths under which this object may be found. Subclasses should provide
        tuples indicating more paths (e.g. via a ToMany relationship).

        This is a MultiPathIndex on the catalog.
        """
        return IPathReporter(self._context).getPaths()

    def name(self):
        """
        The name of the object.
        """
        try:
            return self._context.titleOrId()
        except AttributeError:
            return self._context.id

    def modified(self):
        """
        The last time this object was indexed.

        This is a FieldIndex on the catalog.
        """
        return str(time.time())

    def productionState(self):
        """
        Production state. Only for Devices.
        """

    def collectors(self):
        """
        Collectors. Only for Components.
        """

    def monitored(self):
        """
        Whether or not monitored. Only for Components.
        """


class ComponentWrapper(IndexableWrapper):
    adapts(DeviceComponent)

    def monitored(self):
        if self._context.monitored():
            return 1
        return 0

    def collectors(self):
        return self._context.getCollectors()


class DeviceWrapper(IndexableWrapper):
    adapts(Device)

    def productionState(self):
        return str(self._context.getProdState())


class GlobalCatalog(ZCatalog):

    id = 'global_catalog'

    def __init__(self):
        ZCatalog.__init__(self, self.getId())

    def searchResults(self, **kw):
        user = getSecurityManager().getUser()
        kw['allowedRolesAndUsers'] = _allowedRoles(user)
        return ZCatalog.searchResults(self, **kw)

    def unrestrictedSearchResults(self, **kw):
        return ZCatalog.searchResults(self, **kw)

    def catalog_object(self, obj, **kwargs):
        ob = IIndexableWrapper(obj)
        ZCatalog.catalog_object(self, ob, **kwargs)

    def index_object_under_paths(self, obj, paths):
        p = '/'.join(obj.getPrimaryPath())
        uid = self._catalog.uids.get(p, None)
        if uid:
            idx = self._catalog.getIndex('path')
            idx.index_paths(uid, paths)

    def unindex_object_from_paths(self, obj, paths):
        p = '/'.join(obj.getPrimaryPath())
        uid = self._catalog.uids.get(p, None)
        if uid:
            idx = self._catalog.getIndex('path')
            idx.unindex_paths(uid, paths)



def createGlobalCatalog(portal):
    catalog = GlobalCatalog()

    cat = catalog._catalog
    cat.addIndex('id', makeCaseSensitiveFieldIndex('id'))
    cat.addIndex('name', makeCaseInsensitiveFieldIndex('name'))
    cat.addIndex('modified', makeCaseSensitiveFieldIndex('modified'))
    cat.addIndex('objectImplements', makeCaseSensitiveKeywordIndex('objectImplements'))
    cat.addIndex('allowedRolesAndUsers', makeCaseSensitiveKeywordIndex('allowedRolesAndUsers'))
    cat.addIndex('productionState', makeCaseSensitiveFieldIndex('productionState'))
    cat.addIndex('monitored', makeCaseSensitiveFieldIndex('monitored'))
    cat.addIndex('path', makeMultiPathIndex('path'))
    cat.addIndex('collectors', makeCaseSensitiveKeywordIndex('collectors'))
    cat.addIndex('productKeys', makeCaseSensitiveKeywordIndex('productKeys'))

    catalog.addColumn('id')
    catalog.addColumn('name')
    catalog.addColumn('modified')
    catalog.addColumn('monitored')
    catalog.addColumn('productionState')
    catalog.addColumn('collectors')

    portal._setOb(catalog.getId(), catalog)

