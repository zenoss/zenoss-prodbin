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
""" Unit tests for FSImage module.

$Id: test_FSImage.py 37972 2005-08-16 20:54:10Z jens $
"""
import unittest
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from os.path import join as path_join

from Products.CMFCore.tests.base.dummy import DummyCachingManager
from Products.CMFCore.tests.base.testcase import FSDVTest
from Products.CMFCore.tests.base.testcase import RequestTest


class FSImageTests( RequestTest, FSDVTest):

    def setUp(self):
        FSDVTest.setUp(self)
        RequestTest.setUp(self)

    def tearDown(self):
        RequestTest.tearDown(self)
        FSDVTest.tearDown(self)

    def _makeOne( self, id, filename ):

        from Products.CMFCore.FSImage import FSImage

        return FSImage( id, path_join(self.skin_path_name, filename) )

    def _extractFile( self ):

        path = path_join(self.skin_path_name, 'test_image.gif')
        f = open( path, 'rb' )
        try:
            data = f.read()
        finally:
            f.close()

        return path, data

    def test_ctor( self ):

        path, ref = self._extractFile()

        image = self._makeOne( 'test_image', 'test_image.gif' )
        image = image.__of__( self.root )

        self.assertEqual( image.get_size(), len( ref ) )
        self.assertEqual( image._data, ref )

    def test_index_html( self ):

        path, ref = self._extractFile()

        import os
        from webdav.common import rfc1123_date

        mod_time = os.stat( path )[ 8 ]

        image = self._makeOne( 'test_image', 'test_image.gif' )
        image = image.__of__( self.root )

        data = image.index_html( self.REQUEST, self.RESPONSE )

        self.assertEqual( len( data ), len( ref ) )
        self.assertEqual( data, ref )
        # ICK!  'HTTPResponse.getHeader' doesn't case-flatten the key!
        self.assertEqual( self.RESPONSE.getHeader( 'Content-Length'.lower() )
                        , str(len(ref)) )
        self.assertEqual( self.RESPONSE.getHeader( 'Content-Type'.lower() )
                        , 'image/gif' )
        self.assertEqual( self.RESPONSE.getHeader( 'Last-Modified'.lower() )
                        , rfc1123_date( mod_time ) )

    def test_index_html_with_304( self ):

        path, ref = self._extractFile()

        import os
        from webdav.common import rfc1123_date

        mod_time = os.stat( path )[ 8 ]

        image = self._makeOne( 'test_image', 'test_image.gif' )
        image = image.__of__( self.root )

        self.REQUEST.environ[ 'IF_MODIFIED_SINCE'
                            ] = '%s;' % rfc1123_date( mod_time+3600 )

        data = image.index_html( self.REQUEST, self.RESPONSE )

        self.assertEqual( data, '' )
        # test that we don't supply a content-length
        self.assertEqual( self.RESPONSE.getHeader('Content-Length'.lower()),
                                                  None )
        self.assertEqual( self.RESPONSE.getStatus(), 304 )

    def test_index_html_without_304( self ):

        path, ref = self._extractFile()

        import os
        from webdav.common import rfc1123_date

        mod_time = os.stat( path )[ 8 ]

        image = self._makeOne( 'test_image', 'test_image.gif' )
        image = image.__of__( self.root )

        self.REQUEST.environ[ 'IF_MODIFIED_SINCE'
                            ] = '%s;' % rfc1123_date( mod_time-3600 )

        data = image.index_html( self.REQUEST, self.RESPONSE )

        self.failUnless( data, '' )
        self.assertEqual( self.RESPONSE.getStatus(), 200 )

    def test_caching( self ):
        self.root.caching_policy_manager = DummyCachingManager()
        original_len = len(self.RESPONSE.headers)
        image = self._makeOne('test_image', 'test_image.gif')
        image = image.__of__(self.root)
        image.index_html(self.REQUEST, self.RESPONSE)
        headers = self.RESPONSE.headers
        self.failUnless(len(headers) >= original_len + 3)
        self.failUnless('foo' in headers.keys())
        self.failUnless('bar' in headers.keys())
        self.assertEqual(headers['test_path'], '/test_image')


    def test_index_html_with_304_and_caching( self ):

        # See collector #355
        self.root.caching_policy_manager = DummyCachingManager()
        original_len = len(self.RESPONSE.headers)
        path, ref = self._extractFile()

        import os
        from webdav.common import rfc1123_date

        mod_time = os.stat( path )[ 8 ]

        image = self._makeOne( 'test_image', 'test_image.gif' )
        image = image.__of__( self.root )

        self.REQUEST.environ[ 'IF_MODIFIED_SINCE'
                            ] = '%s;' % rfc1123_date( mod_time+3600 )

        data = image.index_html( self.REQUEST, self.RESPONSE )

        self.assertEqual( data, '' )
        self.assertEqual( self.RESPONSE.getStatus(), 304 )

        headers = self.RESPONSE.headers
        self.failUnless(len(headers) >= original_len + 3)
        self.failUnless('foo' in headers.keys())
        self.failUnless('bar' in headers.keys())
        self.assertEqual(headers['test_path'], '/test_image')

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(FSImageTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
