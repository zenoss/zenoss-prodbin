##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit tests for CachingPolicyManager module.

$Id: test_CachingPolicyManager.py 38666 2005-09-28 16:16:48Z davisg $
"""
import base64
import os

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from App.Common import rfc1123_date
from DateTime.DateTime import DateTime
from AccessControl.SecurityManagement import newSecurityManager

from Products.CMFCore.tests.base.testcase import RequestTest
from Products.CMFCore.tests.base.testcase import FSDVTest
from Products.CMFCore.tests.test_FSPageTemplate import FSPTMaker
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.dummy import DummyUserFolder
from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummyTool
from Products.CMFCore.FSPageTemplate import FSPageTemplate
from Products.CMFCore import CachingPolicyManager


ACCLARK = DateTime( '2001/01/01' )
portal_owner = 'portal_owner'


class DummyContent2:

    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, modified ):
        self.modified = modified

    def Type( self ):
        return 'Dummy'

    def modified( self ):
        return self.modified


class CachingPolicyTests(TestCase):

    def setUp(self):
        self._epoch = DateTime(0)

    def _makePolicy( self, policy_id, **kw ):
        from Products.CMFCore.CachingPolicyManager import CachingPolicy

        return CachingPolicy( policy_id, **kw )

    def _makeContext( self, **kw ):
        from Products.CMFCore.CachingPolicyManager import createCPContext
        return createCPContext( DummyContent2(self._epoch)
                              , 'foo_view', kw, self._epoch )

    def test_empty( self ):
        policy = self._makePolicy( 'empty' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0], 'Last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )

    def test_noPassPredicate( self ):

        policy = self._makePolicy( 'noPassPredicate', predicate='nothing' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

    def test_typePredicate( self ):

        policy = self._makePolicy( 'typePredicate'
                           , predicate='python:object.Type() == "Dummy"' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0] , 'Last-modified' )
        self.assertEqual( headers[0][1] , rfc1123_date(self._epoch.timeTime()) )

    def test_typePredicateMiss( self ):

        policy = self._makePolicy( 'typePredicate'
                        , predicate='python:object.Type() == "Foolish"' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

    def test_viewPredicate( self ):

        policy = self._makePolicy( 'viewPredicate'
                                 , predicate='python:view == "foo_view"' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0], 'Last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )

    def test_viewPredicateMiss( self ):

        policy = self._makePolicy( 'viewPredicateMiss'
                           , predicate='python:view == "bar_view"' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

    def test_kwPredicate( self ):

        policy = self._makePolicy( 'kwPredicate'
                                 , predicate='python:"foo" in keywords.keys()' )
        context = self._makeContext( foo=1 )
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0], 'Last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )

    def test_kwPredicateMiss( self ):

        policy = self._makePolicy( 'kwPredicateMiss'
                                 , predicate='python:"foo" in keywords.keys()' )
        context = self._makeContext( bar=1 )
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

    def test_mtimeFunc( self ):

        policy = self._makePolicy( 'mtimeFunc'
                                 , mtime_func='string:2001/01/01' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0], 'Last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(ACCLARK.timeTime()) )

    def test_mtimeFuncNone( self ):

        policy = self._makePolicy( 'mtimeFuncNone'
                                 , mtime_func='nothing' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )

    def test_maxAge( self ):

        policy = self._makePolicy( 'aged', max_age_secs=86400 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'expires' )
        self.assertEqual( headers[1][1]
                        , rfc1123_date((self._epoch+1).timeTime()) )
        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1] , 'max-age=86400' )

    def test_sMaxAge( self ):

        policy = self._makePolicy( 's_aged', s_max_age_secs=86400 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 's-maxage=86400' )
        self.assertEqual(policy.getSMaxAgeSecs(), 86400)

    def test_noCache( self ):

        policy = self._makePolicy( 'noCache', no_cache=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'pragma' )
        self.assertEqual( headers[1][1] , 'no-cache' )
        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1] , 'no-cache' )

    def test_noStore( self ):

        policy = self._makePolicy( 'noStore', no_store=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'no-store' )

    def test_mustRevalidate( self ):

        policy = self._makePolicy( 'mustRevalidate', must_revalidate=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'must-revalidate' )

    def test_proxyRevalidate( self ):

        policy = self._makePolicy( 'proxyRevalidate', proxy_revalidate=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'proxy-revalidate' )
        self.assertEqual(policy.getProxyRevalidate(), 1)

    def test_public( self ):

        policy = self._makePolicy( 'public', public=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'public' )
        self.assertEqual(policy.getPublic(), 1)

    def test_private( self ):

        policy = self._makePolicy( 'private', private=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'private' )
        self.assertEqual(policy.getPrivate(), 1)

    def test_noTransform( self ):

        policy = self._makePolicy( 'noTransform', no_transform=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'no-transform' )
        self.assertEqual(policy.getNoTransform(), 1)

    def test_lastModified( self ):

        policy = self._makePolicy( 'lastModified', last_modified=0 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 0 )
        self.assertEqual(policy.getLastModified(), 0)

    def test_preCheck( self ):

        policy = self._makePolicy( 'preCheck', pre_check=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'pre-check=1' )
        self.assertEqual(policy.getPreCheck(), 1)
        self.assertEqual(policy.getPostCheck(), None)

    def test_postCheck( self ):

        policy = self._makePolicy( 'postCheck', post_check=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'cache-control' )
        self.assertEqual( headers[1][1] , 'post-check=1' )
        self.assertEqual(policy.getPostCheck(), 1)
        self.assertEqual(policy.getPreCheck(), None)

    def test_ETag( self ):

        # With an empty etag_func, no ETag should be produced
        policy = self._makePolicy( 'ETag', etag_func='' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 1)
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )

        policy = self._makePolicy( 'ETag', etag_func='string:foo' )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 2)
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower(), 'etag' )
        self.assertEqual( headers[1][1], 'foo' )

    def test_combined( self ):

        policy = self._makePolicy( 'noStore', no_cache=1, no_store=1 )
        context = self._makeContext()
        headers = policy.getHeaders( context )

        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'pragma' )
        self.assertEqual( headers[1][1] , 'no-cache' )
        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1] , 'no-cache, no-store' )


class CachingPolicyManagerTests(TestCase):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.CachingPolicyManager import CachingPolicyManager

        return CachingPolicyManager(*args, **kw)

    def setUp(self):

        self._epoch = DateTime()

    def assertEqualDelta( self, lhs, rhs, delta ):
        self.failUnless( abs( lhs - rhs ) <= delta )

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.CachingPolicyManager import CachingPolicyManager
        from Products.CMFCore.interfaces.CachingPolicyManager \
                import CachingPolicyManager as ICachingPolicyManager

        verifyClass(ICachingPolicyManager, CachingPolicyManager)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import ICachingPolicyManager
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.CachingPolicyManager import CachingPolicyManager

        verifyClass(ICachingPolicyManager, CachingPolicyManager)

    def test_empty( self ):

        mgr = self._makeOne()

        self.assertEqual( len( mgr.listPolicies() ), 0 )
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={}
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 0 )

        self.assertRaises( KeyError, mgr._updatePolicy
                         , 'xyzzy', None, None, None, None, None, None, '', '', None, None, None, None, None )
        self.assertRaises( KeyError, mgr._removePolicy, 'xyzzy' )
        self.assertRaises( KeyError, mgr._reorderPolicy, 'xyzzy', -1 )

    def test_addAndUpdatePolicy( self ):

        mgr = self._makeOne()
        mgr.addPolicy( 'first', 'python:1', 'mtime', 1, 0, 1, 0, 'vary', 'etag', None, 2, 1, 0, 1, 0, 1, 0, 2, 3 )
        p = mgr._policies['first']
        self.assertEqual(p.getPolicyId(), 'first')
        self.assertEqual(p.getPredicate(), 'python:1')
        self.assertEqual(p.getMTimeFunc(), 'mtime')
        self.assertEqual(p.getMaxAgeSecs(), 1)
        self.assertEqual(p.getNoCache(), 0)
        self.assertEqual(p.getNoStore(), 1)
        self.assertEqual(p.getMustRevalidate(), 0)
        self.assertEqual(p.getVary(), 'vary')
        self.assertEqual(p.getETagFunc(), 'etag')
        self.assertEqual(p.getSMaxAgeSecs(), 2)
        self.assertEqual(p.getProxyRevalidate(), 1)
        self.assertEqual(p.getPublic(), 0)
        self.assertEqual(p.getPrivate(), 1)
        self.assertEqual(p.getNoTransform(), 0)
        self.assertEqual(p.getEnable304s(), 1)
        self.assertEqual(p.getLastModified(), 0)
        self.assertEqual(p.getPreCheck(), 2)
        self.assertEqual(p.getPostCheck(), 3)
        
        mgr.updatePolicy( 'first', 'python:0', 'mtime2', 2, 1, 0, 1, 'vary2', 'etag2', None, 1, 0, 1, 0, 1, 0, 1, 3, 2 )
        p = mgr._policies['first']
        self.assertEqual(p.getPolicyId(), 'first')
        self.assertEqual(p.getPredicate(), 'python:0')
        self.assertEqual(p.getMTimeFunc(), 'mtime2')
        self.assertEqual(p.getMaxAgeSecs(), 2)
        self.assertEqual(p.getNoCache(), 1)
        self.assertEqual(p.getNoStore(), 0)
        self.assertEqual(p.getMustRevalidate(), 1)
        self.assertEqual(p.getVary(), 'vary2')
        self.assertEqual(p.getETagFunc(), 'etag2')
        self.assertEqual(p.getSMaxAgeSecs(), 1)
        self.assertEqual(p.getProxyRevalidate(), 0)
        self.assertEqual(p.getPublic(), 1)
        self.assertEqual(p.getPrivate(), 0)
        self.assertEqual(p.getNoTransform(), 1)
        self.assertEqual(p.getEnable304s(), 0)
        self.assertEqual(p.getLastModified(), 1)
        self.assertEqual(p.getPreCheck(), 3)
        self.assertEqual(p.getPostCheck(), 2)

    def test_reorder( self ):

        mgr = self._makeOne()

        policy_ids = ( 'foo', 'bar', 'baz', 'qux' )

        for policy_id in policy_ids:
            mgr._addPolicy( policy_id
                          , 'python:"%s" in keywords.keys()' % policy_id
                          , None, 0, 0, 0, 0, '', '' )

        ids = tuple( map( lambda x: x[0], mgr.listPolicies() ) )
        self.assertEqual( ids, policy_ids )

        mgr._reorderPolicy( 'bar', 3 )

        ids = tuple( map( lambda x: x[0], mgr.listPolicies() ) )
        self.assertEqual( ids, ( 'foo', 'baz', 'qux', 'bar' ) )

    def _makeOneWithPolicies( self ):

        mgr = self._makeOne()

        policy_tuples = ( ( 'foo', None  )
                        , ( 'bar', 0     )
                        , ( 'baz', 3600  )
                        , ( 'qux', 86400 )
                        )

        for policy_id, max_age_secs in policy_tuples:
            mgr._addPolicy( policy_id
                          , 'python:"%s" in keywords.keys()' % policy_id
                          , None, max_age_secs, 0, 0, 0, '', '' )

        return mgr

    def test_lookupNoMatch( self ):

        mgr = self._makeOneWithPolicies()
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={}
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 0 )

    def test_lookupMatchFoo( self ):

        mgr = self._makeOneWithPolicies()
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={ 'foo' : 1 }
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 1 )
        self.assertEqual( headers[0][0].lower(), 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )

    def test_lookupMatchBar( self ):

        mgr = self._makeOneWithPolicies()
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={ 'bar' : 1 }
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'expires' )
        self.assertEqual( headers[1][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1], 'max-age=0' )

    def test_lookupMatchBaz( self ):

        mgr = self._makeOneWithPolicies()
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={ 'baz' : 1 }
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'expires' )

        exp_time = DateTime( headers[1][1] )
        target = self._epoch + ( 1.0 / 24.0 )
        self.assertEqualDelta( exp_time, target, 0.01 )

        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1] , 'max-age=3600' )

    def test_lookupMatchQux( self ):

        mgr = self._makeOneWithPolicies()
        headers = mgr.getHTTPCachingHeaders( content=DummyContent2(self._epoch)
                                           , view_method='foo_view'
                                           , keywords={ 'qux' : 1 }
                                           , time=self._epoch
                                           )
        self.assertEqual( len( headers ), 3 )
        self.assertEqual( headers[0][0].lower() , 'last-modified' )
        self.assertEqual( headers[0][1]
                        , rfc1123_date(self._epoch.timeTime()) )
        self.assertEqual( headers[1][0].lower() , 'expires' )

        exp_time = DateTime( headers[1][1] )
        target = self._epoch + 1.0
        self.assertEqualDelta( exp_time, target, 0.01 )

        self.assertEqual( headers[2][0].lower() , 'cache-control' )
        self.assertEqual( headers[2][1] , 'max-age=86400' )


class CachingPolicyManager304Tests(RequestTest, FSDVTest):

    def setUp(self):
        RequestTest.setUp(self)
        FSDVTest.setUp(self)

        now = DateTime()

        # Create a fake portal and the tools we need
        self.portal = DummySite(id='portal').__of__(self.root)
        self.portal._setObject('portal_types', DummyTool())

        # This is a FSPageTemplate that will be used as the View for 
        # our content objects. It doesn't matter what it returns.
        path = os.path.join(self.skin_path_name, 'testPT2.pt')
        self.portal._setObject('dummy_view', FSPageTemplate('dummy_view', path))

        uf = self.root.acl_users
        password = 'secret'
        uf.userFolderAddUser(portal_owner, password, ['Manager'], [])
        user = uf.getUserById(portal_owner)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(uf)
        newSecurityManager(None, user)
        owner_auth = '%s:%s' % (portal_owner, password)
        self.auth_header = "Basic %s" % base64.encodestring(owner_auth)
        
        self.portal._setObject('doc1', DummyContent('doc1'))
        self.portal._setObject('doc2', DummyContent('doc2'))
        self.portal._setObject('doc3', DummyContent('doc3'))
        self.portal.doc1.modified_date = now
        self.portal.doc2.modified_date = now
        self.portal.doc3.modified_date = now

        CachingPolicyManager.manage_addCachingPolicyManager(self.portal)
        cpm = self.portal.caching_policy_manager

        # This policy only applies to doc1. It will not emit any ETag header
        # but it enables If-modified-since handling.
        cpm.addPolicy(policy_id = 'policy_no_etag',
                      predicate = 'python:object.getId()=="doc1"',
                      mtime_func = '',
                      max_age_secs = 0,
                      no_cache = 0,
                      no_store = 0,
                      must_revalidate = 0,
                      vary = '',
                      etag_func = '',
                      enable_304s = 1)

        # This policy only applies to doc2. It will emit an ETag with 
        # the constant value "abc" and also enable if-modified-since handling.
        cpm.addPolicy(policy_id = 'policy_etag',
                      predicate = 'python:object.getId()=="doc2"',
                      mtime_func = '',
                      max_age_secs = 0,
                      no_cache = 0,
                      no_store = 0,
                      must_revalidate = 0,
                      vary = '',
                      etag_func = 'string:abc',
                      enable_304s = 1)

        # This policy only applies to doc3. Etags with constant values of
        # "abc" are emitted, but if-modified-since handling is turned off.
        cpm.addPolicy(policy_id = 'policy_disabled',
                      predicate = 'python:object.getId()=="doc3"',
                      mtime_func = '',
                      max_age_secs = 0,
                      no_cache = 0,
                      no_store = 0,
                      must_revalidate = 0,
                      vary = '',
                      etag_func = 'string:abc',
                      enable_304s = 0)


    def tearDown(self):
        RequestTest.tearDown(self)
        FSDVTest.tearDown(self)


    def _cleanup(self):
        # Clean up request and response
        req = self.portal.REQUEST

        for header in ( 'IF_MODIFIED_SINCE'
                      , 'HTTP_AUTHORIZATION'
                      , 'IF_NONE_MATCH'
                      ):
            if req.environ.get(header, None) is not None:
                del req.environ[header]

        req.RESPONSE.setStatus(200)


    def testUnconditionalGET(self):
        # In this case the Request does not specify any if-modified-since
        # value to take into account, thereby completely circumventing any
        # if-modified-since handling. This must not produce a response status
        # of 304, regardless of any other headers.
        self.portal.doc1()
        response = self.portal.REQUEST.RESPONSE
        self.assertEqual(response.getStatus(), 200)


    def testConditionalGETNoETag(self):
        yesterday = DateTime() - 1
        doc1 = self.portal.doc1
        request = doc1.REQUEST
        response = request.RESPONSE

        # If doc1 has beeen modified since yesterday (which it has), we want
        # the full rendering.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(yesterday)
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc1()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # If doc1 has been modified since its creation (which it hasn't), we
        # want the full rendering. This must return a 304 response.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc1.modified_date)
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc1() 
        self.assertEqual(response.getStatus(), 304)
        self._cleanup()

        # ETag handling is not enabled in the policy for doc1, so asking for
        # one will not produce any matches. We get the full rendering.
        request.environ['IF_NONE_MATCH'] = '"123"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc1()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # We are asking for an ETag as well as modifications after doc2 has 
        # been created. Both won't match and wwe get the full rendering.
        request.environ['IF_NONE_MATCH'] = '"123"'
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc1.modified_date)
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc1()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()


    def testConditionalGETETag(self):
        yesterday = DateTime() - 1
        doc2 = self.portal.doc2
        request = doc2.REQUEST
        response = request.RESPONSE

        # Has doc2 been modified since yesterday? Yes it has, so we get the
        # full rendering.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(yesterday)
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # If doc2 has not been modified since its creation (which it hasn't),
        # we would get a 304 here. However, the policy for doc2 also expects
        # to get an ETag in the request, which we are not setting here. So
        # the policy fails and we get a full rendering.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc2.modified_date)
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # Now we are setting an ETag in our request, but an ETag that does not
        # match the policy's expected value. The policy fails and we get the
        # full rendering.
        request.environ['IF_NONE_MATCH'] = '"123"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # Here we provide the correct and matching ETag value, and we don't
        # specify any if-modified-since condition. This is enough for our
        # policy to trigger 304.
        request.environ['IF_NONE_MATCH'] = '"abc"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 304)
        self._cleanup()
        
        # We specify an ETag and a modification time condition that dooes not 
        # match, so we get the full rendering
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc2.modified_date)
        request.environ['IF_NONE_MATCH'] = '"123"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        # We hand in a matching modified time condition which is supposed to
        # trigger full rendering. This will lead the ETag condition to be
        # overrridden.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(yesterday)
        request.environ['IF_NONE_MATCH'] = '"abc"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()
        
        # Now we pass an ETag that matches the policy and a modified time
        # condition that is not fulfilled. It is safe to serve a 304.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc2.modified_date)
        request.environ['IF_NONE_MATCH'] = '"abc"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc2()
        self.assertEqual(response.getStatus(), 304)
        self._cleanup()

        
    def testConditionalGETDisabled(self):
        yesterday = DateTime() - 1
        doc3 = self.portal.doc3
        request = doc3.REQUEST
        response = request.RESPONSE

        # Our policy disables any 304-handling, so even though the ETag matches
        # the policy, we will get the full rendering.
        request.environ['IF_NONE_MATCH'] = '"abc"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc3()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()
        
        # Now both the ETag and the modified condition would trigger a 304
        # response *if* 304-handling was enabled. It is not in our policy, so
        # we get the full rendering again.
        request.environ['IF_MODIFIED_SINCE'] = rfc1123_date(doc3.modified_date)
        request.environ['IF_NONE_MATCH'] = '"abc"'
        request.environ['HTTP_AUTHORIZATION'] = self.auth_header
        doc3()
        self.assertEqual(response.getStatus(), 200)
        self._cleanup()

        
def test_suite():
    return TestSuite((
        makeSuite(CachingPolicyTests),
        makeSuite(CachingPolicyManagerTests),
        makeSuite(CachingPolicyManager304Tests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')

