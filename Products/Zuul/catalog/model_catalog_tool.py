

import logging

from Acquisition import aq_parent, Implicit
from interfaces import IModelCatalog, IModelCatalogTool
from .model_catalog import ModelCatalogUnavailableError
from Products.AdvancedQuery import Eq, Or, Generic, And, In, MatchRegexp
from Products.ZCatalog.interfaces import ICatalogBrain
from Products.Zuul.catalog.interfaces import IModelCatalog
from Products.Zuul.utils import dottedname, allowedRolesAndGroups
from zenoss.modelindex.exceptions import SearchException
from zenoss.modelindex.searcher import SearchParams
from zenoss.modelindex.constants import INDEX_UNIQUE_FIELD as UID
from zope.interface import implements
from zope.component import getUtility

log = logging.getLogger("model_catalog_tool")


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


class ModelCatalogTool(object):
    """ Search the model catalog """

    implements(IModelCatalogTool)

    def __init__(self, context):
        self.context = context
        self.model_catalog = getUtility(IModelCatalog)

    def is_model_catalog_enabled(self):
        return self.model_catalog.searcher is not None

    def _build_query(self, types=(), paths=(), depth=None, query=None, filterPermissions=True, globFilters=None):
        """
        Build and AdvancedQuery query

        @params types: list/tuple of values for objectImplements field
        @params globFilters: dict with user passed field: value filters
        @params query: AdvancedQuery passed by the user. Most of the time None
        @param filterPermissions: Boolean indicating whether to check for user perms or not

        @return: tuple (AdvancedQuery query, not indexed filters dict)
        """
        available_indexes = self.model_catalog.searcher.get_indexes()
        not_indexed_user_filters = {} # Filters that use not indexed fields

        user_filters_query = None
        types_query = None
        paths_query = None
        permissions_query = None

        partial_queries = []

        if query:
            partial_queries.append(query)

        # Build query from filters passed by user
        if globFilters:
            for key, value in globFilters.iteritems():
                if key in available_indexes:
                    if user_filters_query:
                        user_filters_query = And(query, MatchRegexp(key, '*%s*' % value))
                    else:
                        user_filters_query = MatchRegexp(key, '*%s*' % value)
                else:
                    not_indexed_user_filters[key] = value

        if user_filters_query:
            partial_queries.append(user_filters_query)

        # Build the objectImplements query
        if not isinstance(types, (tuple, list)):
            types = (types,)
        types_query_list = [ Eq('objectImplements', dottedname(t)) for t in types ]
        if len(types_query_list) > 1:
            types_query = Or(*types_query_list)
        else:
            types_query = types_query_list[0]

        if types_query:
            partial_queries.append(types_query)

        # Build query for paths
        if not paths:
            paths = ('/'.join(self.context.getPhysicalPath()) + '*', )
        elif isinstance(paths, basestring):
            paths = (paths,)

        """  OLD CODE. Why this instead of In?  What do we need depth for?
        q = {'query':paths}
        if depth is not None:
            q['depth'] = depth
        paths_query = Generic('path', q)
        """
        paths_query = In('path', paths)

        if paths_query:
            partial_queries.append(paths_query)

        # filter based on permissions
        if filterPermissions:
            permissions_query = In('allowedRolesAndUsers', allowedRolesAndGroups(self.context))

        if permissions_query:
            partial_queries.append(permissions_query)

        # Put together all queries
        search_query = And(*partial_queries)

        return (search_query, not_indexed_user_filters)


    def _search_model_catalog(self, query, start=0, limit=None, order_by=None, reverse=False):
        """
        @returns: SearchResults
        """
        catalog_results = []
        brains = []
        count = 0
        search_params = SearchParams(query, start=start, limit=limit, order_by=order_by, reverse=reverse)
        try:
            catalog_results = self.model_catalog.searcher.search(search_params)
        except SearchException as e:
            log.error("EXCEPTION: {0}".format(e.message))
            raise ModelCatalogUnavailableError()
            
        else:
            for result in catalog_results.results:
                brain = ModelCatalogBrain(result)
                brain = brain.__of__(self.context.dmd)
                brains.append(brain)
            count = catalog_results.total_count

        return SearchResults(iter(brains), total=count, hash_=str(count))


    def search(self, types=(), start=0, limit=None, orderby='name',
               reverse=False, paths=(), depth=None, query=None,
               hashcheck=None, filterPermissions=True, globFilters=None):
        """
        Build and execute a query against the global catalog.
        @param query: Advanced Query query
        @param globFilters: dict {field: value}
        """
        if not self.is_model_catalog_enabled():
            return None
        
        available_indexes = self.model_catalog.searcher.get_indexes()
        # if orderby is not an index then query results will be unbrained and sorted
        areBrains = orderby in available_indexes or orderby is None
        queryOrderby = orderby if areBrains else None
        
        query, not_indexed_user_filters = self._build_query(types, paths, depth, query, filterPermissions, globFilters)

        #areBrains = len(not_indexed_user_filters) == 0

        # if we have not indexed fields, we need to get all the results and manually filter and sort
        # I guess that with solr we should be able to avoid searching by unindexed fields
        #
        # @TODO get all results if areBrains == False
        #
        
        catalog_results = self._search_model_catalog(query, start=start, limit=limit, order_by=orderby, reverse=reverse)

        # @TODO take care of unindexed filters
        return catalog_results


    def getBrain(self, path):
        """
        Gets the brain representing the object defined at C{path}.
        The search is done by uid field
        """
        if not self.is_model_catalog_enabled():
            return None

        if not isinstance(path, (tuple, basestring)):
            path = '/'.join(path.getPhysicalPath())
        elif isinstance(path, tuple):
            path = '/'.join(path)

        if "dmd" in path:
            splitted = path.split('/')
            pos = splitted.index("dmd")
            path = '/'.join(splitted[pos+1:])

        query = Eq(UID, path)
        search_results = self._search_model_catalog(query)

        brain = None
        if search_results.total > 0:
            brain = search_results.results.next()
        else:
            log.error("Unable to get brain. Trying to reindex: %s", path)
            # @TODO reindex the object if we did not find it        
        return brain


    def parents(self, path):
        """
        Get brains representing parents of C{path} + C{path}. Good for making
        breadcrumbs without waking up all the actual parent objects.
        """
        pass

    def count(self, types=(), path=None, filterPermissions=True):
        """
        Get the count of children matching C{types} under C{path}.

        This is cheap; the lazy list returned from a catalog search knows its
        own length without exhausting its contents.

        @param types: Classes or interfaces that should be matched
        @type types: tuple
        @param path: The path under which children should be counted. Defaults
        to the path of C{self.context}.
        @type path: str
        @return: The number of children matching.
        @rtype: int
        """

        if not self.is_model_catalog_enabled():
            return None

        if path is None:
            path = '/'.join(self.context.getPhysicalPath())
        if not path.endswith('*'):
            path = path + '*'
        query, _ = self._build_query(types=types, paths=(path,), filterPermissions=filterPermissions)
        search_results = self._search_model_catalog(query)

        """ #  OLD CODEEE had some caching stuff
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
        """
        return search_results.total

    def update(self, obj):
        self.model_catalog.catalog_object(obj)


class ModelCatalogBrain(Implicit):
    implements(ICatalogBrain)
    
    def __init__(self, result):
        """
        Modelindex result wrapper
        @param result: modelindex.zenoss.modelindex.search.SearchResult
        """
        self._result = result
        #self.dmd = context.dmd

    def has_key(self, key):
        return self.__contains__(key)

    def __contains__(self, name):
        return hasattr(self._result, name)

    def getPath(self):
        """ Get the physical path for this record """
        uid = str(self._result.uid)
        if not uid.startswith('/zport/dmd/'):
            uid = '/zport/dmd/' + uid
        return uid

    def _unrestrictedGetObject(self):
        """ """
        return self.getObject()

    def getObject(self):
        """Return the object for this record

        Will return None if the object cannot be found via its cataloged path
        (i.e., it was deleted or moved without recataloging), or if the user is
        not authorized to access the object.
        """
        parent = aq_parent(self)
        obj = None
        try:
            obj = parent.unrestrictedTraverse(self.getPath()) 
        except:
            log.error("Unable to get object from brain. Path: {0}. Catalog may be out of sync.".format(self._result.uid))
        return obj

    def getRID(self):
        """Return the record ID for this object."""
        return self._result.uuid
