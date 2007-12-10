##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import unittest

from Products.PluggableAuthService.tests.conformance \
     import ILoginPasswordHostExtractionPlugin_conformance
from Products.PluggableAuthService.tests.conformance \
     import IChallengePlugin_conformance
from Products.PluggableAuthService.tests.conformance \
     import ICredentialsUpdatePlugin_conformance
from Products.PluggableAuthService.tests.conformance \
     import ICredentialsResetPlugin_conformance

from Products.PluggableAuthService.tests.test_PluggableAuthService \
     import FauxRequest, FauxResponse, FauxObject, FauxRoot, FauxContainer

class FauxSettableRequest(FauxRequest):

    def set(self, name, value):
        self._dict[name] = value

class FauxCookieResponse(FauxResponse):

    def __init__(self):
        self.cookies = {}
        self.redirected = False
        self.status = '200'
        self.headers = {}

    def setCookie(self, cookie_name, cookie_value, path):
        self.cookies[(cookie_name, path)] = cookie_value

    def expireCookie(self, cookie_name, path):
        if (cookie_name, path) in self.cookies:
            del self.cookies[(cookie_name, path)]

    def redirect(self, location, status=302, lock=0):
        self.status = status
        self.headers['Location'] = location

class CookieAuthHelperTests( unittest.TestCase
                           , ILoginPasswordHostExtractionPlugin_conformance
                           , IChallengePlugin_conformance
                           , ICredentialsResetPlugin_conformance
                           ):

    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.CookieAuthHelper \
            import CookieAuthHelper

        return CookieAuthHelper

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id=id, *args, **kw )

    def _makeTree( self ):

        rc = FauxObject( 'rc' )
        root = FauxRoot( 'root' ).__of__( rc )
        folder = FauxContainer( 'folder' ).__of__( root )
        object = FauxObject( 'object' ).__of__( folder )

        return rc, root, folder, object

    def test_extractCredentials_no_creds( self ):

        helper = self._makeOne()
        response = FauxCookieResponse()
        request = FauxRequest(RESPONSE=response)

        self.assertEqual( helper.extractCredentials( request ), {} )

    def test_extractCredentials_with_form_creds( self ):

        helper = self._makeOne()
        response = FauxCookieResponse()
        request = FauxSettableRequest(__ac_name='foo',
                                      __ac_password='bar',
                                      RESPONSE=response)

        self.assertEqual(len(response.cookies), 0)
        self.assertEqual(helper.extractCredentials(request),
                        {'login': 'foo',
                         'password': 'bar',
                         'remote_host': '',
                         'remote_address': ''})
        self.assertEqual(len(response.cookies), 0)

    def test_extractCredentials_with_deleted_cookie(self):
        # http://www.zope.org/Collectors/PAS/43
        # Edge case: The ZPublisher sets a cookie's value to "deleted"
        # in the current request if expireCookie is called. If we hit
        # extractCredentials in the same request after this, it would 
        # blow up trying to deal with the invalid cookie value.
        helper = self._makeOne()
        response = FauxCookieResponse()
        req_data = { helper.cookie_name : 'deleted'
                   , 'RESPONSE' : response
                   }
        request = FauxSettableRequest(**req_data)
        self.assertEqual(len(response.cookies), 0)

        self.assertEqual(helper.extractCredentials(request), {})

    def test_challenge( self ):
        from zExceptions import Unauthorized
        rc, root, folder, object = self._makeTree()
        response = FauxCookieResponse()
        request = FauxRequest(RESPONSE=response)
        root.REQUEST = request

        helper = self._makeOne().__of__(root)

        helper.challenge(request, response)
        self.assertEqual(response.status, 302)
        self.assertEqual(len(response.headers), 1)


    def test_resetCredentials( self ):
        helper = self._makeOne()
        response = FauxCookieResponse()
        request = FauxRequest(RESPONSE=response)

        helper.resetCredentials(request, response)
        self.assertEqual(len(response.cookies), 0)

    def test_loginWithoutCredentialsUpdate( self ):
        helper = self._makeOne()
        response = FauxCookieResponse()
        request = FauxSettableRequest( __ac_name='foo'
                                     , __ac_password='bar'
                                     , RESPONSE=response
                                     )
        request.form = {'came_from':''}
        helper.REQUEST = request

        helper.login()
        self.assertEqual(len(response.cookies), 0)


if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( CookieAuthHelperTests ),
        ))

