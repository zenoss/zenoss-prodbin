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

from itertools import islice
from zope.interface import implements
from Products.AdvancedQuery import Eq, Or, Generic, And
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from Products.Zuul.interfaces import ITreeNode, ICatalogTool
from Products.Zuul.utils import dottedname


class TreeNode(object):
    """
    Adapts a brain.
    """
    implements(ITreeNode)

    def __init__(self, brain):
        if not isinstance(brain, AbstractCatalogBrain):
            brain = ICatalogTool(brain).getBrain(brain)
            if brain is None:
                raise Exception('brain is None')
        self._object = brain

    @property
    def uid(self):
        return self._object.getPath()

    @property
    def path(self):
        """
        Get the tree path for an object by querying the catalog.

        This is cheaper than modifying getPrimaryPath(), which has to wake up
        each parent object just to get its id.
        """
        brains = ICatalogTool(self._object).parents(self.uid)
        # Lop off dmd, which is always first (zport isn't indexed)
        if brains[0].id=='dmd':
            brains = brains[1:]
        return '/'.join(b.id for b in brains)

    @property
    def id(self):
        return self._object.getPath().replace('/', '.')

    @property
    def text(self):
        return self._object.name

    @property
    def _evsummary(self):
        raise NotImplementedError

    @property
    def iconCls(self):
        for sev, count in self._evsummary:
            if count:
                break
        else:
            sev = 'clear'
        return 'severity-icon-small %s' % sev

    @property
    def children(self):
        raise NotImplementedError

    def __repr__(self):
        return "<TreeNode %s>" % self.uid


class SearchResults(object):
    def __hash__(self):
        return self.hash_

    def __init__(self, results, total, hash_):
        self.hash_ = hash_
        self.results = results
        self.total = total

    def __iter__(self):
        return self.results


class CatalogTool(object):
    implements(ICatalogTool)

    def __init__(self, context):
        self.context = context
        self.catalog = context.getPhysicalRoot().zport.global_catalog

    def getBrain(self, path):
        # Make sure it's actually a path
        if not isinstance(path, (tuple, basestring)):
            path = path.getPhysicalPath()
        if isinstance(path, tuple):
            path = '/'.join(path)
        brains = self.catalog(path={'query':path, 'depth':0})
        if brains:
            return brains[0]

    def parents(self, path):
        # Make sure it's actually a path
        if not isinstance(path, (tuple, basestring)):
            path = path.getPhysicalPath()
        brains = self.catalog(path={'query':path, 'navtree':True, 'depth':0})
        # Sort to ensure order
        return sorted(brains, key=lambda b:b.getPath())

    def count(self, types=(), path=None):
        if path is None:
            path = '/'.join(self.context.getPhysicalPath())
        results = self._queryCatalog(types, orderby=None, paths=(path,))
        return len(results)

    def _queryCatalog(self, types=(), orderby='name', reverse=False, paths=(),
                     depth=None, query=None):
        qs = []
        if query is not None:
            qs.append(query)

        # Build the path query
        if not paths:
            paths = ('/'.join(self.context.getPhysicalPath()),)
        q = {'query':paths}
        if depth is not None:
            q['depth'] = depth
        pathq = Generic('path', q)
        qs.append(pathq)

        # Build the type query
        if not isinstance(types, (tuple, list)):
            types = (types,)
        subqs = (Eq('objectImplements', dottedname(t)) for t in types)
        typeq = Or(*subqs)
        qs.append(typeq)

        # Consolidate into one query
        query = And(*qs)

        # Sort information
        if orderby:
            if reverse:
                sortinfo = (orderby, 'desc')
            else:
                sortinfo = (orderby, 'asc')
            args = (query, (sortinfo,))
        else:
            args = (query,)

        # Get the brains
        result = self.catalog.evalAdvancedQuery(*args)
        return result

    def search(self, types=(), start=0, limit=None, orderby='name',
               reverse=False, paths=(), depth=None, query=None):
        brains = self._queryCatalog(types, orderby, reverse, paths, depth,
                                    query)
        totalCount = len(brains)
        hash_ = hash(tuple(b.getRID() for b in brains))

        # Return a slice
        if limit is None:
            stop = None
        else:
            stop = start + limit
        results = islice(brains, start, stop)

        return SearchResults(results, totalCount, hash_)

    def update(self, obj):
        self.catalog.catalog_object(obj, idxs=())


