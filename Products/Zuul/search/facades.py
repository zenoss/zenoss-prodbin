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
    implements(IParsedQuery)

    def __init__(self, _operators, _keywords):
        self.operators = _operators
        self.keywords = _keywords

class DefaultQueryParser(object):
    implements(ISearchQueryParser)

    def parse(self, query):
        keywords = []
        operators = {}

        for phrase in self._phrasify(query):
            pair = phrase.split(':',1)
            if len(pair) == 1 or pair[0] == '':
                keywords.append(phrase)
            else:
                if pair[0] not in operators:
                    operators[pair[0]]=[]
                operators[pair[0]].append(pair[1])

        return ParsedQuery( operators, keywords )

    def _phrasify(self, string):
        string = string.replace('"', "'")
        phrases = []
        for i, segment in enumerate(string.split("'")):
            if i % 2:
                phrases.append(segment)
            else:
                phrases.extend(segment.split(' '))
        return [ p for p in phrases if p != '' ]


class SearchFacade(ZuulFacade):
    """
    Facade for search stuff.
    """
    implements(ISearchFacade)

    def __init__(self, context):
        ZuulFacade.__init__(self, context)

    def _getParser(self):
        return getGlobalSiteManager().queryUtility( ISearchQueryParser )

    def _getProviders(self):
        return subscribers([self._dmd], ISearchProvider)

    def _getSearchResults(self, query, maxResultsPerProvider=None):
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

        return results

    def getSearchResults(self, query):
        return self._getSearchResults( query )

    def getQuickSearchResults(self, query):
        return self._getSearchResults(query, 5)

    def noProvidersPresent(self):
        subscribers = self._getProviders()
        return subscribers is None or len(subscribers) == 0
    
