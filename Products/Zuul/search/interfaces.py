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

from zope.interface import Attribute, Interface

from Products.Zuul.interfaces import IFacade, IMarshallable

class IParsedQuery(Interface):
    """
    An set of operators and keywords resulting from the parsing of
    an input query
    """
    operators = Attribute("A hashtable of operator names to lists of values")
    keywords = Attribute("A list of keywords")


class ISearchQueryParser(Interface):
    """
    Interface for query parser implementation.  Will be returned from an
    adapter lookup so that the default parser can be replaced if needed.
    """

    def parse( query ):
        """
        Take a query and return an IParsedQuery object
        """

class ISearchProvider(Interface):
    """
    Implement this interface to provide search results.
    """

    def getSearchResults(parsedQuery, sorter):
        """
        Returns a list of ISearchResult objects based on the given
        IParsedQuery.
        """

    def getQuickSearchResults(parsedQuery, sorter):
        """
        Returns a list of ISearchResult objects based on the given
        IParsedQuery.  These ISearchResults may be only partially filled
        out.
        """


class ISearchResult(IMarshallable):
    """
    Implement this interface to allow objects to appear in search results.
    """

    url = Attribute("Most direct URL to the represented object")
    category = Attribute("Search category of the represented object")
    excerpt = Attribute("Small descriptive snippet for the represented object.")
    icon = Attribute("URL to the 16x16 icon for the represented object")
    popout = Attribute("True/false whether to open link in new window")


class ISearchFacade(IFacade):
    """
    Interface for a search facade.
    """
    def getQuickSearchResults(self, queryString, searchResultSorter):
        """
        Query for items, return ISearchInfo objects

        @param searchResultSorter an optional ISearchResultSorter-implementing
               object
        """

    def getSearchResults(self, queryString, searchResultSorter):
        """
        Query for items, returning ISearchInfo objects

        @param searchResultSorter an optional ISearchResultSorter-implementing
               object
        """

    def noProvidersPresent(self):
        """
        Return true if there are no providers
        """

class ISearchResultSorter(Interface):
    """
    Sort ISearchResult objects.  (The default sort is by category then excerpt.)
    """
    comparator = Attribute("Comparator for sorting search results")
    maxResults = Attribute("Maximum results to be returned from a query")
    maxResultsPerCategory = Attribute("Maximum results of any one category to" +
                                      " be returned from a query")
    def limitSort(results):
        """
        Limits and sorts search results
        """

class IQuickSearchResultSnippet(IMarshallable):
    """
    Represents the snippet of html that will be placed in the right side of
    the quick search drop down for a search result.
    """
    category = Attribute("Search category of the represented object")
    content = Attribute("The content of the search result drop down")
    url = Attribute("Link to the represented object")
    popout = Attribute("True/false whether to open link in new window")
    
class IQuickResultSnippetFactory( Interface):
    """
    return an IQuickSearchResultSnippet to be included in displayed results
    """
