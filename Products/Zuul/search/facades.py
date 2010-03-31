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

from itertools import islice, ifilter
from zope.component import subscribers
from zope.interface import implements
from zope.component import getGlobalSiteManager
from Products.Zuul.facades import ZuulFacade

from interfaces import ISearchFacade
from interfaces import ISearchProvider
from interfaces import ISearchQueryParser
from interfaces import IParsedQuery
from Products.Zuul.search import ISearchResultSorter


class ParsedQuery(object):
    """
    A canonical representation of the query contents
    to be passed to an ISearchProvider.  Currently, this is only operators
    and keywords.
    """
    implements(IParsedQuery)

    def __init__(self, _operators={}, _keywords=[]):
        self.operators = _operators
        self.keywords = _keywords


def _phrasify(string):
    """
    Tokenize a string by whitespace, respecting double-quotes
    @rtype: list

    >>> _phrasify( 'a b c' )
    ['a', 'b', 'c']
    >>> _phrasify( '"a b" c' )
    ['a b', 'c']
    >>> _phrasify( '     a b' )
    ['a', 'b']
    >>> _phrasify( '"a     b" c' )
    ['a     b', 'c']
    """
    string = string.replace('"', "'")
    phrases = []
    for i, segment in enumerate(string.split("'")):
        if i % 2:
            phrases.append(segment)
        else:
            phrases.extend(segment.split(' '))
    return [ p for p in phrases if p != '' ]


class DefaultQueryParser(object):
    """
    The default implementation of ISearchQueryParser that converts a plain
    text string into a set of operators and keywords, i.e., a ParsedQuery.
    """
    implements(ISearchQueryParser)

    def parse(self, query):
        """
        For each atom in a the query string,
        categorize into keywords and operator-value pairs.
        Operators are name-value pairs separated by a colon (:).
        Keywords are anything else.

        @type query string
        @rtype IParsedQuery

        >>> parser = DefaultQueryParser()
        >>> parser.parse( 'a b c' ).keywords
        ['a', 'b', 'c']
        >>> parser.parse( 'a b c' ).operators
        {}
        >>> parser.parse( 'a:b c' ).keywords
        ['c']
        >>> parser.parse( 'a:b c' ).operators
        {'a':['b']}
        >>> parser.parse( 'a:b c:d a:e f g:' ).keywords
        ['f', 'g:']
        >>> parser.parse( 'a:b c:d a:e f g:' ).operators
        {'a':['b', 'e'], 'c':['d']}
        
        """
        keywords = []
        operators = {}

        for phrase in _phrasify(query):
            pair = phrase.split(':',1)
            if len(pair) == 1 or pair[0] == '':
                keywords.append(phrase)
            else:
                if pair[0] not in operators:
                    operators[pair[0]]=[]
                operators[pair[0]].append(pair[1])

        return ParsedQuery( operators, keywords )


DEVICE_CATEGORY = 'device'
EVENT_CATEGORY = 'event'

class DefaultSearchResultSorter(object):
    implements(ISearchResultSorter)

    def __call__(self, result1, result2):
        result = self._compareCategories( result1, result2 )
        if result == 0:
            result = self._compareExcerpts( result1, result2 )
        return result

    def _compareCategories(self, result1, result2):
        cat1 = result1.category.lower()
        cat2 = result2.category.lower()

        if cat1 == cat2:
            return 0
        elif cat1 == DEVICE_CATEGORY or cat1 == EVENT_CATEGORY:
            return 1 if cat2 == DEVICE_CATEGORY else -1
        elif cat2 == DEVICE_CATEGORY or cat2 == EVENT_CATEGORY:
            return 1
        else:
            return cmp( cat1, cat2 )

    def _compareExcerpts(self, result1, result2 ):
        return cmp( result1.excerpt, result2.excerpt )


DEFAULT_SORTER = DefaultSearchResultSorter()


class SearchFacade(ZuulFacade):
    """
    Facade for search functionality.  The SearchFacade distributes queries to
    multiple search providers and returns them as ISearchResults.
    """
    implements(ISearchFacade)

    def __init__(self, context):
        ZuulFacade.__init__(self, context)

    def _getParser(self):
        return getGlobalSiteManager().queryUtility( ISearchQueryParser )

    def _getProviders(self):
        return subscribers([self._dmd], ISearchProvider)

    def _filterResultsByCategoryCount(self, results, maxPerCategory ):
        # If no max, just return the results
        if maxPerCategory is None:
            return results
        
        # We assume the results are sorted by category.
        # Take the first maxPerCategory of each group.
        categoryCounts={}
        def stillBelowCategoryLimit( result ):
            category = result.category
            if category not in categoryCounts:
                categoryCounts[category] = 0
            categoryCounts[category] += 1
            return categoryCounts[category] <= maxPerCategory

        return ifilter( stillBelowCategoryLimit, results )
        

    def _getSearchResults(self, query, maxResults=None,
                          maxResultsPerCategory=None,
                          resultSorter=DEFAULT_SORTER):
        """
        The actual implementation of querying each provider.  This consists
        of parsing the query, sending it to the providers, and limiting
        the results if necessary.

        @param query The raw query string
        @param maxResults The maximum number of results to be returned
        @param maxResultsPerCategory The maximum number of results to be
                                     returned of any one category
        @return ordered list of ISearchResult objects
        """
        parser = self._getParser()
        parsedQuery = parser.parse( query )

        results = []
        for adapter in self._getProviders():
            # Go ahead and look for maxResults from each provider.  This may
            # artificially limit the number of results for an individual
            # category, but most algorithms will do some sort of artificial
            # limiting unless the queries are performed in concert.
            providerResults = adapter.getSearchResults( parsedQuery,
                                                        maxResults )
            if providerResults:
                results.extend( providerResults )

        # Sort results
        results.sort( resultSorter )

        # Keep only max number of results per category
        if maxResultsPerCategory is not None:
            results = self._filterResultsByCategoryCount( results,
                                                maxResultsPerCategory )

        # Keep max number of results
        results = islice(results, maxResults)

        return results

    def getSearchResults(self, query, resultSorter=DEFAULT_SORTER):
        """
        Execute the query against registered search providers, returning
        full results.

        @param query query string
        @rtype list of ISearchResult-implementing objects
        """
        return self._getSearchResults( query, resultSorter=resultSorter )

    def getQuickSearchResults(self, query, maxResults=None,
                              maxResultsPerCategory=None,
                              resultSorter=DEFAULT_SORTER):
        """
        Execute the query against registered search providers, returning
        abbreviated results for display in the quick search drop-down list.

        @param query query string
        @rtype list of ISearchResult-implementing objects
        """
        return self._getSearchResults(query,
                                      maxResults,
                                      maxResultsPerCategory,
                                      resultSorter=resultSorter)

    def noProvidersPresent(self):
        """
        Check for existence of search providers

        @rtype boolean
        """
        subscribers = self._getProviders()
        return subscribers is None or len(subscribers) == 0
    
