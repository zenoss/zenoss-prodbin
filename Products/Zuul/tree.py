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
from Products.AdvancedQuery import Eq, Or, Generic, And, In
from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
from Products.Zuul.interfaces import ITreeNode, ICatalogTool
from Products.Zuul.utils import dottedname, unbrain, allowedRolesAndGroups
from Products.Zuul.utils import UncataloguedObjectException, PathIndexCache
from AccessControl import getSecurityManager


class TreeNode(object):
    """
    Adapts a brain.
    """
    implements(ITreeNode)

    def __init__(self, ob, root=None, parent=None):
        if not isinstance(ob, AbstractCatalogBrain):
            brain = ICatalogTool(ob).getBrain(ob)
            if brain is None:
                raise UncataloguedObjectException(ob)
            else:
                ob = brain
        self._object = ob
        self._root = root or self
        self._parent = parent or None

    def _buildCache(self, orgtype=None, instancetype=None, relname=None,
                    treePrefix=None):
        if orgtype and not getattr(self._root, '_cache', None):
            cat = ICatalogTool(self._object.unrestrictedTraverse(self.uid))
            results = cat.search(orgtype)
            if instancetype:
                instanceresults = cat.search(instancetype)
                self._root._cache = PathIndexCache(results, instanceresults,
                                                   relname, treePrefix)
            else:
                self._root._cache = PathIndexCache(results)
        return self._root._cache

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
        return 'tree-severity-icon-small-%s' % sev

    @property
    def children(self):
        raise NotImplementedError

    def __repr__(self):
        return "<TreeNode %s>" % self.uid

    @property
    def hidden(self):
        """
        Make sure we don't show the root node of a tree
        if we don't have permission on it or any of its children
        """
        # make sure we are looking at a root node
        pieces = self.uid.split('/')
        if len(pieces) != 4:
            return False
        
        # check for our permission
        manager = getSecurityManager()
        obj = self._object.unrestrictedTraverse(self.uid)
        if manager.checkPermission("View", obj):
            return False
        
        # search the catalog to see if we have permission with any of the children
        cat = ICatalogTool(obj)
        numInstances = cat.count('Products.ZenModel.DeviceOrganizer.DeviceOrganizer', self.uid)
        # if anything is returned we have view permissions on a child
        return not numInstances > 0


class StaleResultsException(Exception):
    """
    The hash check failed. Selections need to be refreshed.
    """


class SearchResults(object):

    def __init__(self, results, total, hash_, areBrains=True):
        self.results = results
        self.total = total
        self.hash_ = hash_
        self.areBrains = areBrains

    def __hash__(self):
        return self.hash_

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

        # filter based on permissions
        qs.append(In('allowedRolesAndUsers', allowedRolesAndGroups(self.context)))
                
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
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None):

        # if orderby is not an index then _queryCatalog, then query results
        # will be unbrained and sorted
        areBrains = orderby in self.catalog.getIndexes()
        queryOrderby = orderby if areBrains else None

        queryResults = self._queryCatalog(types, queryOrderby, reverse, paths, depth, query)
        totalCount = len(queryResults)
        if areBrains or not queryResults:
            allResults = queryResults
            hash_ = hash( tuple(r.getRID() for r in queryResults) )
        else:
            allResults = self._sortQueryResults(queryResults, orderby, reverse)
            hash_ = hash( tuple(r.getPrimaryPath() for r in allResults) )

        if hashcheck is not None:
            if hash_ != int(hashcheck):
                raise StaleResultsException("Search results do not match")

        # Return a slice
        start = max(start, 0)
        if limit is None:
            stop = None
        else:
            stop = start + limit
        results = islice(allResults, start, stop)

        return SearchResults(results, totalCount, str(hash_), areBrains)

    def update(self, obj):
        self.catalog.catalog_object(obj, idxs=())

    def _sortQueryResults(self, queryResults, orderby, reverse):

        # save the values during sorting in case getting the value is slow
        savedValues = {}

        def getValue(obj):
            key = obj.getPrimaryPath()
            if key in savedValues:
                value = savedValues[key]
            else:
                value = getattr(obj, orderby)
                if callable(value):
                    value = value()
                savedValues[key] = value
            return value

        def compareValues(left, right):
            return cmp( getValue(left), getValue(right) )

        allObjects = [unbrain(brain) for brain in queryResults]
        allObjects.sort(cmp=compareValues, reverse=reverse)
        return allObjects
