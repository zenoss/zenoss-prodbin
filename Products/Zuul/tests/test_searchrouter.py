######################################################################
#
# Copyright 2010 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

import os.path
from zope.component import getGlobalSiteManager
from zope.component import adapts
from zope.interface import implements

from Products.ZenModel.DataRoot import DataRoot
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.interfaces import IFacade
from Products.Zuul.search.interfaces import ISearchFacade
from Products.Zuul.search.interfaces import ISearchResult
from Products.Zuul.search.routers import SearchRouter
from Products.Zuul.interfaces import IMarshaller
from Products.Zuul.marshalling import Marshaller


import logging
log = logging.getLogger("zen.search")

search_results = None

class DummyFacade(object):
    implements( ISearchFacade )
    adapts( DataRoot )
    
    def __init__(self,dmd):
        pass

    def getSearchResults( self, query ):
        return search_results

    def getQuickSearchResults(self, query):
        return search_results

class DummySearchInfo(object):
    implements( ISearchResult )

    def __init__(self, url, category, excerpt, icon):
        self.url = url
        self.category = category
        self.excerpt = excerpt
        self.icon = icon

search_results = None

def _createDummyInfo( index ):
    return DummySearchInfo(
        'url%s' % index,
        'cat%s' % index,
        'exc%s' % index,
        'icon%s' % index
        )
        
def _createJSONInfo( index ):
    return {'category': 'cat%s' % index,
            'url': 'url%s' % index,
            'excerpt': 'exc%s' % index,
            'icon': 'icon%s' % index}

class TestSearchRouter(BaseTestCase):
    
    def setUp(self):
        global search_results
        BaseTestCase.setUp(self)
        search_results = None
        gsm = getGlobalSiteManager()
        gsm.registerAdapter( DummyFacade, (DataRoot,), IFacade, 'search' )
        gsm.registerAdapter( Marshaller, (ISearchResult,), IMarshaller )

    def tearDown(self):
        global search_results
        search_results = None
        gsm = getGlobalSiteManager()
        gsm.unregisterAdapter( DummyFacade )
        gsm.unregisterAdapter( Marshaller )

    def testGetLiveResults(self):
        global search_results
        search_results = [
            _createDummyInfo(1)
            ]
        router = SearchRouter()
        varResults = router.getLiveResults( 'query' )
        self.assertEquals( {'results':
                            [_createJSONInfo(1)] },
                           varResults )

    def testMultipleGetLiveResults(self):
        global search_results
        search_results = [ _createDummyInfo(x) for x in range(1,8)]
        router = SearchRouter()
        varResults = router.getLiveResults( 'query' )
        self.assertEquals( {'results':
                            [ _createJSONInfo(y) for y in range(1,8)]},
                           varResults )
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestSearchRouter))
    return suite
