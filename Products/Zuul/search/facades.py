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

from zope.component import subscribers
from zope.interface import implements
from zope.component import getGlobalSiteManager
from Products.Zuul.facades import ZuulFacade

from interfaces import ISearchFacade
from interfaces import ISearchProvider
from interfaces import ISearchQueryParser
from interfaces import IParsedQuery


class ParsedQuery(object):
    """
    A canonical representation of the query contents
    to be passed to an ISearchProvider.  Currently, this is only operators
    and keywords.
    """
    implements(IParsedQuery)

    def __init__(self, _operators, _keywords):
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
        if maxPerCategory is None:
            return results
        resultCounts={}

        def keepResult( result ):
            doKeep = False
            if result.category not in resultCounts:
                resultCounts[result.category] = 0
            if resultCounts[result.category] != maxPerCategory:
                resultCounts[result.category] += 1
                doKeep = True
            return doKeep

        return filter( keepResult, results )

    def _getSearchResults(self, query, maxResultsPerProvider=None,
                          maxResultsPerCategory=None):
        parser = self._getParser()
        parsedQuery = parser.parse( query )
        operators = parsedQuery.operators
        keywords = parsedQuery.keywords

        results = []
        for adapter in self._getProviders():
            providerResults = adapter.getSearchResults(operators, keywords)
            if maxResultsPerProvider is not None:
                results.extend( providerResults[:maxResultsPerProvider] )
            else:
                results.extend( providerResults )

        results.sort( lambda x,y: cmp(x.excerpt,y.excerpt) )

        if maxResultsPerCategory is not None:
            results = self._filterResultsByCategoryCount( results,
                                                maxResultsPerCategory )

        return results

    def getSearchResults(self, query):
        """
        Execute the query against registered search providers, returning
        full results.

        @param query query string
        @rtype list of ISearchResult-implementing objects
        """
        return self._getSearchResults( query )

    def getQuickSearchResults(self, query):
        """
        Execute the query against registered search providers, returning
        abbreviated results for display in the quick search drop-down list.

        @param query query string
        @rtype list of ISearchResult-implementing objects
        """
        return self._getSearchResults(query, None, 5)

    def noProvidersPresent(self):
        """
        Check for existence of search providers

        @rtype boolean
        """
        subscribers = self._getProviders()
        return subscribers is None or len(subscribers) == 0
    
