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

class FauxInlineResponse(FauxResponse):

    def __init__(self):
        self.setBody("Should never see this.")
        self.status = '200'
        self.headers = {}

    def setStatus(self, status, reason=None):
        self.status = status

    def setBody(self, body, *args, **kw):
        self.body = body

class InlineAuthHelperTests( unittest.TestCase
                           , ILoginPasswordHostExtractionPlugin_conformance
                           , IChallengePlugin_conformance
                           ):

    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.InlineAuthHelper \
            import InlineAuthHelper

        return InlineAuthHelper

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
        response = FauxInlineResponse()
        request = FauxRequest(RESPONSE=response)

        self.assertEqual( helper.extractCredentials( request ), {} )

    def test_extractCredentials_with_form_creds( self ):

        helper = self._makeOne()
        response = FauxInlineResponse()
        request = FauxSettableRequest(__ac_name='foo',
                                      __ac_password='bar',
                                      RESPONSE=response)

        self.assertEqual(helper.extractCredentials(request),
                        {'login': 'foo',
                         'password': 'bar',
                         'remote_host': '',
                         'remote_address': ''})

    def test_challenge( self ):
        from zExceptions import Unauthorized
        rc, root, folder, object = self._makeTree()
        response = FauxInlineResponse()
        request = FauxRequest(RESPONSE=response)
        root.REQUEST = request

        helper = self._makeOne().__of__(root)
        helper.body = "Overridden"

        self.assertEqual(response.body, "Should never see this.")
        helper.challenge(request, response)
        self.assertEqual(response.body, "Overridden")

if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( InlineAuthHelperTests ),
        ))

