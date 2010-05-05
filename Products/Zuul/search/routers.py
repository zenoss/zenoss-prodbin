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
from Products.ZenUtils.Ext import DirectRouter
from Products import Zuul
from Products.Zuul.search import ISearchResult
from Products.Zuul.search import IQuickSearchResultSnippet
from Products.Zuul.search import DefaultSearchResultSorter
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
        groupedResult = itertools.groupby(results, lambda x: x.category)
        return {'results': Zuul.marshal(groupedResult),
                'total': len(list(results))}

    def noProvidersPresent(self):
        return self._getFacade().noProvidersPresent()
    
