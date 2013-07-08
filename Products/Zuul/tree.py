##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
import re
import sre_constants
from itertools import islice
from zope.interface import implements
from BTrees.OOBTree import OOBTree
from BTrees.IIBTree import IIBTree
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.Zuul.interfaces import ITreeNode, ICatalogTool, IInfo
from Products.Zuul.utils import dottedname, unbrain, allowedRolesAndGroups
from Products.Zuul.utils import UncataloguedObjectException, PathIndexCache
from AccessControl import getSecurityManager
from Products.Zuul.infos import InfoBase
from Products.Zuul import getFacade
from Products.Zuul.decorators import memoize
from Products.ZenUtils.NaturalSort import natural_compare
import logging
log = logging.getLogger("zen.tree")


class TreeNode(object):
    """
    Adapts a brain.
    """
    implements(ITreeNode)

    def __init__(self, ob, root=None, parent=None):
        self._root = root or self
        if getattr(self._root, '_ob_cache', None) is None:
            self._root._ob_cache = {}
        if not ICatalogBrain.providedBy(ob):
            brain = ICatalogTool(ob).getBrain(ob)
            if brain is None:
                raise UncataloguedObjectException(ob)
            # We already have the object - cache it here so _get_object doesn't
            # have to look it up again.
            self._root._ob_cache[brain.getPath()] = ob
            ob = brain
        self._object = ob
        self._parent = parent or None
        self._severity = None
        # allow showing the event severity icons to be configurable
        if not hasattr(self._root, 'showSeverityIcons'):
            self._root._showSeverityIcons = self._shouldShowSeverityIcons()

    def _shouldShowSeverityIcons(self):
        return self._get_object().dmd.UserInterfaceSettings.getInterfaceSettings().get('showEventSeverityIcons')

    def _get_object(self):
        obj = self._root._ob_cache.get(self.uid)
        if not obj:
            obj = self._object._unrestrictedGetObject()
            self._root._ob_cache[self.uid] = obj
        return obj

    def _buildCache(self, orgtype=None, instancetype=None, relname=None,
                    treePrefix=None, orderby=None):
        if orgtype and not getattr(self._root, '_cache', None):
            cat = ICatalogTool(self._object.unrestrictedTraverse(self.uid))
            results = cat.search(orgtype, orderby=orderby)
            if instancetype:
                instanceresults = cat.search(instancetype, orderby=None)
                self._root._cache = PathIndexCache(results, instanceresults,
                                                   relname, treePrefix)
            else:
                self._root._cache = PathIndexCache(results)
        return self._root._cache

    @property
    def uuid(self):
        return self._object.uuid

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
        return self.uid.replace('/zport/dmd/', '')

    @property
    def id(self):
        return self.uid.replace('/', '.')

    @property
    def text(self):
        return self._object.name

    def setSeverity(self, severity):
        self._severity = severity

    def _loadSeverity(self):
        if self._severity is None:
            if self.uuid:
                zep = getFacade('zep')
                sev = zep.getSeverityName(zep.getWorstSeverity([self.uuid]).get(self.uuid, 0)).lower()
                self._severity = sev
        return self._severity

    @property
    def iconCls(self):
        if self._root._showSeverityIcons:
            sev = self._loadSeverity();
            return self.getIconCls(sev)
        return None

    def getIconCls(self, sev):
        return 'tree-severity-icon-small-%s' % (sev or 'clear')

    @property
    def children(self):
        raise NotImplementedError

    def __repr__(self):
        return "<TreeNode %s>" % self.uid

    @property
    @memoize
    def hidden(self):
        """
        Make sure we don't show the root node of a tree
        if we don't have permission on it or any of its children
        """
        # always show the root Device organizer so restricted users can see
        # all of the devices they have access to
        if self.uid == '/zport/dmd/Devices':
            return False

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



class CountCache(PathIndexCache):
    def __init__(self, results, path, expires):
        PathIndexCache.__init__(self, (), results, (), path)
        self.expires = expires

    def insert(self, idx, results, relnames=None, treePrefix=None):
        unindex = None
        for brain in results:
            # Use the first brain to get a reference to the index, then reuse
            # that reference
            unindex = unindex or brain.global_catalog._catalog.indexes['path']._unindex
            path = brain.getPath()
            if treePrefix and not path.startswith(treePrefix):
                for p in unindex[brain.getRID()]:
                    if p.startswith(treePrefix):
                        path = p
                        break
            path = path.split('/', 3)[-1]
            for depth in xrange(path.count('/')+1):
                comp = idx.setdefault(path, IIBTree())
                comp[depth] = comp.get(depth, 0) + 1
                path = path.rsplit('/', 1)[0]

    def count(self, path, depth=None):
        path = path.split('/', 3)[-1]
        try:
            idx = self._instanceidx[path]
            depth = depth or max(idx.keys())
            return sum(idx[d] for d in xrange(depth+1) if d in idx.keys())
        except KeyError:
            return 0

    @property
    def expired(self):
        return time.time() >= self.expires


class CatalogTool(object):
    implements(ICatalogTool)

    def __init__(self, context):
        self.context = context
        self.catalog = context.getPhysicalRoot().zport.global_catalog
        self.catalog._v_caches = getattr(self.catalog, "_v_caches", OOBTree())


    def getBrain(self, path):
        # Make sure it's actually a path
        if not isinstance(path, (tuple, basestring)):
            path = '/'.join(path.getPhysicalPath())
        elif isinstance(path, tuple):
            path = '/'.join(path)
        cat = self.catalog._catalog
        rid = cat.uids[path]
        if rid:
            return cat.__getitem__(rid)

    def parents(self, path):
        # Make sure it's actually a path
        if not isinstance(path, (tuple, basestring)):
            path = path.getPhysicalPath()
        brains = self.catalog(path={'query':path, 'navtree':True, 'depth':0})
        # Sort to ensure order
        return sorted(brains, key=lambda b:b.getPath())

    def count(self, types=(), path=None, filterPermissions=True):
        if path is None:
            path = '/'.join(self.context.getPhysicalPath())

        # Check for a cache
        caches = self.catalog._v_caches
        types = (types,) if isinstance(types, basestring) else types
        types = tuple(sorted(map(dottedname, types)))
        for key in caches:
            if path.startswith(key):
                cache = caches[key].get(types, None)
                if cache is not None and not cache.expired:
                    return cache.count(path)
        else:
            # No cache; make one
            results = self._queryCatalog(types, orderby=None, paths=(path,), filterPermissions=filterPermissions)
            # cache the results for 5 seconds
            cache = CountCache(results, path, time.time() + 5)
            caches[path] = caches.get(path, OOBTree())
            caches[path][types] = cache
            return len(results)

    def _buildQuery(self, types, paths, depth, query, filterPermissions):
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
        subqs = [Eq('objectImplements', dottedname(t)) for t in types]
        if subqs:
            # Don't unnecessarily nest in an Or if there is only one type query
            typeq = subqs[0] if len(subqs) == 1 else Or(*subqs)
            qs.append(typeq)

        # filter based on permissions
        if filterPermissions:
            qs.append(In('allowedRolesAndUsers', allowedRolesAndGroups(self.context)))

        # Consolidate into one query
        return And(*qs)

    def _buildSort(self, orderby, reverse):
        if orderby:
            if reverse:
                sortinfo = (orderby, 'desc')
            else:
                sortinfo = (orderby, 'asc')
            return (sortinfo,)

    def _queryCatalog(self, types=(), orderby=None, reverse=False, paths=(),
                     depth=None, query=None, filterPermissions=True):
        query = self._buildQuery(types, paths, depth, query, filterPermissions)
        sort = self._buildSort(orderby, reverse)
        args = (query, sort) if sort else (query, )

        # Get the brains
        result = self.catalog.evalAdvancedQuery(*args)
        return result

    def search(self, types=(), start=0, limit=None, orderby=None,
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None, filterPermissions=True, globFilters=None):

        # if orderby is not an index then _queryCatalog, then query results
        # will be unbrained and sorted
        areBrains = orderby in self.catalog._catalog.indexes or orderby is None
        queryOrderby = orderby if areBrains else None
        infoFilters = {}

        if globFilters:
            for key, value in globFilters.iteritems():
                if self.catalog.hasIndexForTypes(types, key):
                    if query:
                        query = And(query, MatchRegexp(key, '(?i).*%s.*' % value))
                    else:
                        query = MatchRegexp(key, '(?i).*%s.*' % value)
                else:
                    areBrains = False
                    infoFilters[key] = value
        try:
            queryResults = self._queryCatalog(types, queryOrderby, reverse, paths, depth, query, filterPermissions)
        except sre_constants.error:
            # if there is an invalid regex in the query return an empty list
            log.error("Invalid regex in the following query: %s" % query)
            queryResults = []

        # see if we need to filter by waking up every object
        if infoFilters:
            queryResults = self._filterQueryResults(queryResults, infoFilters)

        totalCount = len(queryResults)
        hash_ = totalCount
        if areBrains or not queryResults:
            allResults = queryResults
        else:
            allResults = self._sortQueryResults(queryResults, orderby, reverse)

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

    def _filterQueryResults(self, queryResults, infoFilters):
        """
        filters the results by the passed in infoFilters dictionary. If the
        property of the info object is another info object the "name" attribute is used.
        The filters are applied as case-insensitive strings on the attribute of the info object.
        @param queryResults list of brains
        @param infoFilters dict: key/value pairs of filters
        @return list of brains
        """
        if not infoFilters:
            return list(queryResults)

        #Optimizing!
        results = { brain: [True, IInfo(brain.getObject())] for brain in queryResults }
        for key, value in infoFilters.iteritems():
            valRe = re.compile(".*" + value + ".*", re.IGNORECASE)
            for result in results:
                match, info = results[result]
                if not match:
                    continue

                testvalues = getattr(info, key)
                if not hasattr(testvalues, "__iter__"):
                    testvalues = [testvalues]

                # if the property was a dictionary see if the "key" is valid
                # or if it is a dict representation of an info object, then check for the
                # name attribute.
                if isinstance(testvalues, dict):
                    val = testvalues.get(key, testvalues.get('name'))
                    if not (val and valRe.match(str(val))):
                        results[result][0] = False
                else:
                    # if anyone of these values is satisfied then include the object
                    isMatch = False
                    for testVal in testvalues:
                        if isinstance(testVal, InfoBase):
                            testVal = testVal.name
                        if valRe.match(str(testVal)):
                            isMatch = True
                            break
                    if not isMatch:
                        results[result][0] = False
        return [key for key,matches in results.iteritems() if matches[0]]

    def _sortQueryResults(self, queryResults, orderby, reverse):

        # save the values during sorting in case getting the value is slow
        savedValues = {}

        def getValue(obj):
            key = obj.getPrimaryPath()
            if key in savedValues:
                value = savedValues[key]
            else:
                value = getattr(IInfo(obj), orderby)
                if callable(value):
                    value = value()
                # if an info object is returned then sort by the name
                if IInfo.providedBy(value):
                    value = value.name.lower()
                savedValues[key] = value
            return value

        return sorted((unbrain(brain) for brain in queryResults),
                        key=getValue, reverse=reverse, cmp=natural_compare)


class PermissionedCatalogTool(CatalogTool):
    """
    A specialized catalog tool used for searching the other
    catalogs that still have permissions but are not the global
    catalog
    """
    def __init__(self, context, catalog):
        super(PermissionedCatalogTool, self).__init__(context)
        self.catalog = catalog

    def _queryCatalog(self, types=(), orderby=None, reverse=False, paths=(),
                     depth=None, query=None, filterPermissions=True):
        # Identical to global catalog query, except without types
        query = self._buildQuery((), paths, depth, query, filterPermissions)
        sort = self._buildSort(orderby, reverse)
        args = (query, sort) if sort else (query, )

        # Get the brains
        result = self.catalog.evalAdvancedQuery(*args)
        return result
