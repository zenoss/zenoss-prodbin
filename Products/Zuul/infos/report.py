###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import imap, chain

from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.interfaces import IReportClassNode, IReportNode, ICatalogTool
from Products.ZenModel.ReportClass import ReportClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.utils import catalogAwareImap
from Products.Zuul.utils import PathIndexCache
from Products.Zuul.routers.report import essentialReportOrganizers

class ReportClassNode(TreeNode):
    implements(IReportClassNode)
    adapts(ReportClass)

    def _buildCache(self):
        cat = ICatalogTool(self._object.unrestrictedTraverse(self.uid))
        results = []
        results.extend(cat.search('Products.ZenModel.ReportClass.ReportClass',
                orderby=None))
        instanceresults = []
        instancetypes = [
            'Products.ZenModel.Report.Report',
            'Products.ZenModel.DeviceReport.DeviceReport',
            'Products.ZenModel.GraphReport.GraphReport',
            'Products.ZenModel.MultiGraphReport.MultiGraphReport',
        ]
        for instancetype in instancetypes:
            instanceresults.extend(cat.search(instancetype, orderby=None))
        results.extend(instanceresults)
        self._root._cache = PathIndexCache(results, instanceresults)
        return self._root._cache

    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            cache = self._buildCache()
        return cache

    @property
    def children(self):
        kids = self._get_cache.search(self.uid)
        def handler(kid, self):
            if kid.meta_type.endswith("ReportClass"):
                return ReportClassNode(kid, self._root, self)
            else:
                return ReportNode(kid, self._root, self)
        return catalogAwareImap(lambda x:handler(x, self), kids)

    @property
    def leaf(self):
        return False

    @property
    def iconCls(self):
        return 'severity-icon-small clear'

    @property
    def qtip(self):
        return self._object.description

    @property
    def deletable(self):
        return self.uid not in essentialReportOrganizers

    @property
    def meta_type(self):
        return self._object.meta_type

    @property
    def text(self):
        numReports = self._get_cache.count(self.uid)
        return {
            'text': self._object.name,
            'count': numReports,
            'description': 'reports'
        }

    @property
    def edit_url(self):
        return None

class ReportNode(TreeNode):
    implements(IReportNode)
    adapts(ZenModelRM)

    @property
    def leaf(self):
        return True

    @property
    def iconCls(self):
        return 'leaf'

    @property
    def qtip(self):
        return self._object.description

    @property
    def deletable(self):
        return True

    @property
    def meta_type(self):
        return self._object.meta_type

    @property
    def children(self):
        return ()

    @property
    def edit_url(self):
        if self._object.meta_type == 'Report':
            return None
        return "%s/edit%s" % (self.uid, self._object.meta_type)

