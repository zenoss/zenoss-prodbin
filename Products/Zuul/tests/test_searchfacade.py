######################################################################
#
# Copyright 2010 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import os.path
from zope.component import getGlobalSiteManager
from zope.component import adapts
from zope.interface import implements
from zope.interface import providedBy

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from Products.Zuul.search.interfaces import ISearchQueryParser
from Products.Zuul.search.interfaces import IParsedQuery
from Products.Zuul.search.interfaces import ISearchProvider
from Products.Zuul.search.facades import SearchFacade
from Products.Zuul.search.facades import ParsedQuery

import logging
log = logging.getLogger("zen.search")


class DummyParser(object):
    implements( ISearchQueryParser )

    def parse(self, query ):
        return ParsedQuery( {}, [] )

search_results = None

class DummyResult:
    def __init__(self,id,excerpt=None,category='test'):
        self.id = id
        self.excerpt = excerpt
        self.category = category
        
class DummyProvider(object):
    implements( ISearchProvider )
    adapts( object )

    def __init__(self, obj):
        pass

    def getSearchResults(self,parsedQuery,maxResults=None):
        return search_results

def createResultsFromRange( max, category='test' ):
    ids = range(1,max+1)
    return createResultsFromIds(ids,category)

def createResultsFromIds( ids, category='test' ):
    excerpts = map(str,ids)
    categories = [category] * len(ids)
    return map( DummyResult, ids, excerpts, categories )


class TestSearchFacade(BaseTestCase):

    def setUp(self):
        global search_results
        BaseTestCase.setUp(self)
        search_results = None
        gsm = getGlobalSiteManager()
        self._parser = DummyParser()
        gsm.registerUtility( self._parser, ISearchQueryParser )
        gsm.registerSubscriptionAdapter( DummyProvider )

    def tearDown(self):
        global search_results
        search_results = None
        gsm = getGlobalSiteManager()
        gsm.unregisterUtility( self._parser )
        gsm.unregisterSubscriptionAdapter( DummyProvider )

    def testGetQuickSearchResults(self):
        global search_results
        facade = SearchFacade(self.dmd)
        search_results = createResultsFromRange(20)
        results = facade.getQuickSearchResults( "testquery", 10 )
        # Should only have 10 results
        dummyIds = [result.id for result in results
                    if isinstance(result, DummyResult)]
        self.assertEquals( set(range(1,11)), set(dummyIds) )

    def testGetSearchResults(self):
        global search_results
        facade = SearchFacade(self.dmd)
        search_results = createResultsFromRange(25)
        results = facade.getSearchResults( "testquery" )
        dummyIds = [result.id for result in results
                    if isinstance(result, DummyResult)]
        self.assertEquals( set(range(1,26)), set(dummyIds) )

    def testCategoryCountFilter(self):
        global search_results
        search_results = createResultsFromRange(8,'cat1')
        search_results.extend( createResultsFromRange(7,'cat2') )
        facade = SearchFacade(self.dmd)
        results = facade.getQuickSearchResults( "testquery", 20, 5 )
        cat1Ids = [result.id for result in results if result.category == 'cat1']
        cat2Ids = [result.id for result in results if result.category == 'cat2']
        self.assertEquals( set(range(1,6)), set(cat1Ids) )
        self.assertEquals( set(range(1,6)), set(cat2Ids) )

    def testSortByExcerpt(self):
        ids = [6,4,3,2,8,5,9,7,1]
        global search_results
        search_results = createResultsFromIds(ids)
        facade = SearchFacade(self.dmd)
        results = facade.getSearchResults( "testquery" )
        resultIds = [result.id for result in results]
        self.assertEquals( range(1,10), resultIds )

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSearchFacade))
    return suite
