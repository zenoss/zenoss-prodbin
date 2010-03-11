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
from zope.interface import providedBy, ro, implements
from zope.component import adapts
from Acquisition import aq_base
from AccessControl import getSecurityManager
from AccessControl.PermissionRole import rolesForPermissionOn
from Products.CMFCore.utils import _mergedLocalRoles
from Products.ZCatalog.ZCatalog import ZCatalog
from Products.ZenUtils.IpUtil import numbip
from Products.ZenUtils.Search import makeMultiPathIndex
from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseSensitiveKeywordIndex
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenModel.Device import Device
from Products.Zuul.utils import getZProperties

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

    def ipAddress(self):
        """
        IP address associated with this object as 32-bit integer. For devices,
        the manageIp; for interfaces, the first ip address.

        This is a FieldIndex on the catalog.
        """
        getter = getattr(self._context, 'getIpAddress', None)
        if getter is None:
            getter = getattr(self._context, 'getManageIp', None)
        return str(numbip(getter()))

    def zProperties(self):
        """
        A dictionary of all the zProperties associated with this device.
        In the form:
          { 'zCommandTimeOut' : 180 }

        This is on the metadata of the catalog
        """
        return getZProperties(self._context)

    def uid(self):
        """
        Primary path for this object. This is included for sorting purposes;
        obviously it would normally be totally unnecessary, due to
        brain.getPath() being available.

        This is a FieldIndex on the catalog.
        """
        return aq_base(self._context).getPrimaryId().lstrip('/zport/dmd')

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

    def meta_type(self):
        """
        Object's meta_type. Mostly used for backwards compatibility.

        This is a FieldIndex on the catalog and a metadata column.
        """
        return aq_base(self._context).meta_type

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
        
    def searchKeywordsForChildren(self):
        """
        For searchables
        """

    def searchKeywords(self):
        """
        For searchables
        """

    def searchExcerpt(self):
        """
        For searchables
        """

    def searchIcon(self):
        """
        For searchables
        """


class SearchableMixin(object):

    def searchKeywordsForChildren(self):
        return (self._context.titleOrId(),)

    def searchKeywords(self):
        o = self._context
        return self.searchKeywordsForChildren() + (o.meta_type,)

    def searchExcerpt(self):
        return self._context.titleOrId()

    def searchIcon(self):
        return self._context.zIcon


class ComponentWrapper(SearchableMixin,IndexableWrapper):
    adapts(DeviceComponent)

    def monitored(self):
        if self._context.monitored():
            return '1'
        return ''

    def collectors(self):
        return self._context.getCollectors()

    def searchKeywordsForChildren(self):
        o = self._context
        return (o.titleOrId(), o.name(),
            o.monitored() and "monitored" or "unmonitored") + \
            ISearchableWrapper(o.device()).searchKeywordsForChildren()

    def searchExcerpt(self):
        o = self._context
        return '%s <span style="font-size:smaller">(%s)</span>' % (
            o.name(), o.getParentDeviceName())


class DeviceWrapper(SearchableMixin,IndexableWrapper):
    adapts(Device)

    def productionState(self):
        return str(self._context.productionState)

    def searchKeywordsForChildren(self):
        o = self._context
        return (o.titleOrId(),
            o.manageIp, o.hw.serialNumber, o.hw.tag, o.uptimeStr(),
            o.getHWManufacturerName(), o.getHWProductName(),
            o.getOSProductName(), o.getOSManufacturerName(),
            o.getHWSerialNumber(), o.getPerformanceServerName(),
            o.getProductionStateString(), o.getPriorityString(),
            o.getLocationName(),
            o.monitorDevice() and "monitored" or "unmonitored",
            ) \
            + tuple(o.getSystemNames()) + tuple(o.getDeviceGroupNames())

    def searchExcerpt(self):
        o = self._context
        if o.manageIp:
            return '%s <span style="font-size:smaller">(%s)</span>' % (
                o.titleOrId(), o.manageIp)
        else:
            return o.titleOrId()

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
    cat.addIndex('uid', makeCaseSensitiveFieldIndex('uid'))
    cat.addIndex('meta_type', makeCaseSensitiveFieldIndex('meta_type'))
    cat.addIndex('name', makeCaseInsensitiveFieldIndex('name'))
    cat.addIndex('modified', makeCaseSensitiveFieldIndex('modified'))
    cat.addIndex('ipAddress', makeCaseSensitiveFieldIndex('ipAddress'))
    cat.addIndex('objectImplements', makeCaseSensitiveKeywordIndex('objectImplements'))
    cat.addIndex('allowedRolesAndUsers', makeCaseSensitiveKeywordIndex('allowedRolesAndUsers'))
    cat.addIndex('productionState', makeCaseSensitiveFieldIndex('productionState'))
    cat.addIndex('monitored', makeCaseSensitiveFieldIndex('monitored'))
    cat.addIndex('path', makeMultiPathIndex('path'))
    cat.addIndex('collectors', makeCaseSensitiveKeywordIndex('collectors'))
    cat.addIndex('productKeys', makeCaseSensitiveKeywordIndex('productKeys'))
    cat.addIndex('searchKeywords',
        makeCaseInsensitiveKeywordIndex('searchKeywords'))
        
    catalog.addColumn('id')
    catalog.addColumn('name')
    catalog.addColumn('meta_type')
    catalog.addColumn('modified')
    catalog.addColumn('monitored')
    catalog.addColumn('productionState')
    catalog.addColumn('collectors')
    catalog.addColumn('zProperties')
    catalog.addColumn('searchIcon')
    catalog.addColumn('searchExcerpt')

    portal._setOb(catalog.getId(), catalog)

