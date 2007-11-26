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
""" Unit tests for FSDTMLMethod module.

$Id: test_FSDTMLMethod.py 37061 2005-06-15 14:17:41Z tseaver $
"""
from unittest import TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from os.path import join as path_join

from OFS.Folder import Folder
from Products.PageTemplates.TALES import Undefined
from Products.StandardCacheManagers import RAMCacheManager

from Products.CMFCore.FSDTMLMethod import FSDTMLMethod
from Products.CMFCore.FSMetadata import FSMetadata
from Products.CMFCore.tests.base.dummy import DummyCachingManager
from Products.CMFCore.tests.base.dummy import DummyCachingManagerWithPolicy
from Products.CMFCore.tests.base.testcase import FSDVTest
from Products.CMFCore.tests.base.testcase import RequestTest
from Products.CMFCore.tests.base.testcase import SecurityTest
from Products.CMFCore.tests.base.dummy import DummyContent

from DateTime import DateTime

class FSDTMLMaker(FSDVTest):

    def _makeOne( self, id, filename ):
        path = path_join(self.skin_path_name, filename)
        metadata = FSMetadata(path)
        metadata.read()
        return FSDTMLMethod( id, path, properties=metadata.getProperties() )


class FSDTMLMethodTests( RequestTest, FSDTMLMaker ):

    def setUp(self):
        FSDTMLMaker.setUp(self)
        RequestTest.setUp(self)

    def tearDown(self):
        RequestTest.tearDown(self)
        FSDTMLMaker.tearDown(self)

    def test_Call( self ):
        script = self._makeOne( 'testDTML', 'testDTML.dtml' )
        script = script.__of__(self.root)
        self.assertEqual(script(self.root, self.REQUEST), 'foo\n')

    def test_caching( self ):
        #   Test HTTP caching headers.
        self.root.caching_policy_manager = DummyCachingManager()
        original_len = len( self.RESPONSE.headers )
        script = self._makeOne('testDTML', 'testDTML.dtml')
        script = script.__of__(self.root)
        script(self.root, self.REQUEST, self.RESPONSE)
        self.failUnless( len( self.RESPONSE.headers ) >= original_len + 2 )
        self.failUnless( 'foo' in self.RESPONSE.headers.keys() )
        self.failUnless( 'bar' in self.RESPONSE.headers.keys() )

    def test_ownership( self ):
        script = self._makeOne( 'testDTML', 'testDTML.dtml' )
        script = script.__of__(self.root)
        # fsdtmlmethod has no owner
        owner_tuple = script.getOwnerTuple()
        self.assertEqual(owner_tuple, None)

        # and ownership is not acquired [CMF/450]
        self.root._owner= ('/foobar', 'baz')
        owner_tuple = script.getOwnerTuple()
        self.assertEqual(owner_tuple, None)

    def test_304_response_from_cpm( self ):
        # test that we get a 304 response from the cpm via this template

        from webdav.common import rfc1123_date

        mod_time = DateTime()
        self.root.caching_policy_manager = DummyCachingManagerWithPolicy()
        content = DummyContent(id='content')
        content.modified_date = mod_time
        content = content.__of__(self.root)
        script = self._makeOne('testDTML', 'testDTML.dtml')
        script = script.__of__(content)
        self.REQUEST.environ[ 'IF_MODIFIED_SINCE'
                            ] = '%s;' % rfc1123_date( mod_time+3600 )
        data = script(content, self.REQUEST, self.RESPONSE)

        self.assertEqual( data, '' )
        self.assertEqual( self.RESPONSE.getStatus(), 304 )

class FSDTMLMethodCustomizationTests( SecurityTest, FSDTMLMaker ):

    def setUp( self ):
        FSDTMLMaker.setUp(self)
        SecurityTest.setUp( self )

        self.root._setObject( 'portal_skins', Folder( 'portal_skins' ) )
        self.skins = self.root.portal_skins

        self.skins._setObject( 'custom', Folder( 'custom' ) )
        self.custom = self.skins.custom

        self.skins._setObject( 'fsdir', Folder( 'fsdir' ) )
        self.fsdir = self.skins.fsdir

        self.fsdir._setObject( 'testDTML'
                             , self._makeOne( 'testDTML', 'testDTML.dtml' ) )

        self.fsDTML = self.fsdir.testDTML

    def test_customize( self ):

        self.fsDTML.manage_doCustomize( folder_path='custom' )

        self.assertEqual( len( self.custom.objectIds() ), 1 )
        self.failUnless( 'testDTML' in self.custom.objectIds() )

    def test_customize_caching(self):
        # Test to ensure that cache manager associations survive customizing
        cache_id = 'gofast'
        RAMCacheManager.manage_addRAMCacheManager( self.root
                                                 , cache_id
                                                 , REQUEST=None
                                                 )
        self.fsDTML.ZCacheable_setManagerId(cache_id, REQUEST=None)

        self.assertEqual(self.fsDTML.ZCacheable_getManagerId(), cache_id)

        self.fsDTML.manage_doCustomize(folder_path='custom')
        custom_pt = self.custom.testDTML

        self.assertEqual(custom_pt.ZCacheable_getManagerId(), cache_id)

    def tearDown(self):
        SecurityTest.tearDown(self)
        FSDTMLMaker.tearDown(self)


def test_suite():
    return TestSuite((
        makeSuite(FSDTMLMethodTests),
        makeSuite(FSDTMLMethodCustomizationTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
