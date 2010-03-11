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

class DummyProvider(object):
    implements( ISearchProvider )
    adapts( object )

    def __init__(self, obj):
        pass

    def getSearchResults(self,operators,keywords):
        return search_results


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
        search_results = range(1,7)
        results = facade.getQuickSearchResults( "testquery" )
        self.assert_( set(range(1,6)).issubset(set(results)) )

    def testGetSearchResults(self):
        global search_results
        facade = SearchFacade(self.dmd)
        search_results = range(1,7)
        results = facade.getSearchResults( "testquery" )
        self.assert_( set(range(1,7)).issubset(set(results)) )

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSearchFacade))
    return suite
