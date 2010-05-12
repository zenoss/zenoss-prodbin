######################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
######################################################################

from zope.interface import implements
from zope.component import adapts
from AccessControl import getSecurityManager
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products import Zuul
from Products.Zuul.search import ISearchResult
from Products.Zuul.search import IQuickSearchResultSnippet
from Products.Zuul.search import DefaultSearchResultSorter
from Products.Zuul.utils import ZuulMessageFactory as _t
from zope.component import getAllUtilitiesRegisteredFor
from Products.Zuul.search.interfaces import IQuickResultSnippetFactory
import itertools

class DefaultQuickSearchResultSnippet(object):
    """
    Default representation of quick search results.  Converts icon and excerpt
    values from search results into html content for the drop-down combo
    box.
    """
    implements(IQuickSearchResultSnippet)
    adapts(ISearchResult)

    def __init__(self, result):
        self._result = result

    @property
    def category(self):
        return self._result.category

    defaultTemplate = '<table>' + \
                          '<td class="icon">%s</td>' + \
                          '<td class="excerpt">%s</td>' + \
                      '</table>'
    @property
    def content(self):
        return self.defaultTemplate % ( self._result.icon, self._result.excerpt)

    @property
    def url(self):
        return self._result.url

    @property
    def popout(self):
        return self._result.popout
    

_MAX_RESULTS_PER_QUERY=100
_MAX_RESULTS_PER_CATEGORY=10

_RESULT_SORTER = DefaultSearchResultSorter( _MAX_RESULTS_PER_QUERY,
                                            _MAX_RESULTS_PER_CATEGORY )

class SearchRouter(DirectRouter):
    """
    UI specific code for the search functionality.
    """

    def _getFacade(self):
        return Zuul.getFacade('search', self.context)

    def _addAllResultsLink(self, snippets, query):
        extraResults = getAllUtilitiesRegisteredFor(IQuickResultSnippetFactory)
        for factory in extraResults:
            snippets.insert(0, factory()(query))

    def _getLoggedinUserId(self):
        """
        @return String logged in users user id
        """
        securityManager = getSecurityManager()
        return securityManager.getUser()._login
        
    def getLiveResults(self, query):
        """
        Returns IQuickSearchResultSnippets for the results of the query.
        """
        facade = self._getFacade()
        results = facade.getQuickSearchResults(query,
                                               _RESULT_SORTER)
        snippets = []
        for result in results:
            snippet = IQuickSearchResultSnippet( result )
            snippets.append( snippet )
        if snippets:
            self._addAllResultsLink( snippets, query )

        return {'results': Zuul.marshal(snippets)}
    
    def getAllResults(self, query, **kwargs):
        """
        Returns ISearchResultSnippets for the results of the query.
        """
        facade = self._getFacade()
        limits = DefaultSearchResultSorter(maxResultsPerCategory=250)
        results = facade.getSearchResults(query, limits)
        #group by category so we get [ 'category', [SearchResults, ...]]
        results = list(results)
        groupedResult = itertools.groupby(results, lambda x: x.category)
        return {'results': Zuul.marshal(groupedResult),
                'total': len(results)}

    def noProvidersPresent(self):
        return self._getFacade().noProvidersPresent()

    def getSavedSearch(self, searchName):
        """
        @params string searchName: identifier of the search we are looking for
        @return DirectResponse: the data attribute will have our search terms
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.fail(message=_t('Unable to find the specified search'))
        
        # look for our search 
        savedSearch = facade.getSavedSearch(searchName)
        if savedSearch:
            return DirectResponse.succeed(data=Zuul.marshal(savedSearch))

        # we could not find the search term
        return DirectResponse.fail(message=_t('Unable to find the specified search'))
    
    def saveSearch(self, queryString, searchName):
        """
        Adds this search to our collection of saved searches
        @param string queryString: term we are searching for
        @param string searchName: our query string's identifier
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()

        creator = self._getLoggedinUserId()
        
        # save the search
        facade.saveSearch(queryString, searchName, creator)
        return DirectResponse.succeed()

    def getAllSavedSearches(self, query):
        """
        @returns [ISavedSearchInfo] All the searches the logged in
        user can access
        """
        facade = self._getFacade()
        if facade.noSaveSearchProvidersPresent():
            return DirectResponse.succeed()
        
        data = facade.getSavedSearchesByUser()
        return DirectResponse.succeed(data=Zuul.marshal(data))
