##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights
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

from AccessControl.Permissions import view as View

from Products.PluggableAuthService.tests import pastc
from Products.PluggableAuthService.interfaces.plugins import IExtractionPlugin


class CachingTests(pastc.PASTestCase):

    def afterSetUp(self):
        self.pas = self.folder.acl_users
        # Add a RAM cache
        factory = self.pas.manage_addProduct['StandardCacheManagers']
        factory.manage_addRAMCacheManager('ram_cache')
        self.cache = self.pas.ram_cache
        # Activate the cache
        self.pas.ZCacheable_setManagerId('ram_cache')
        # Create a protected document
        self.folder.manage_addDTMLMethod('doc', file='the document')
        self.doc = self.folder.doc
        self.doc.manage_permission(View, [pastc.user_role], acquire=False)

    def assertCacheStats(self, entries, misses, hits):
        # Check cache statistics against expected values
        report_item = {'entries': 0, 'misses': 0, 'hits': 0}
        report = self.cache.getCacheReport()
        if len(report):
            report_item = report[0]
        self.assertEqual(report_item.get('entries'), entries)
        self.assertEqual(report_item.get('misses'), misses)
        self.assertEqual(report_item.get('hits'), hits)

    def test__extractUserIds(self):
        request = self.app.REQUEST
        request._auth = 'Basic %s' % pastc.user_auth

        # Extract, we should see a cache miss
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(1, 1, 0)

        # Extract again, we should see a cache hit
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(1, 1, 1)

        # Extract yet again, we should see another hit
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(1, 1, 2)

    def test__extractUserIds_two_extractors(self):
        # Two extractors should result in two cache entries
        request = self.app.REQUEST
        request._auth = 'Basic %s' % pastc.user_auth

        factory = self.pas.manage_addProduct['PluggableAuthService']
        factory.addHTTPBasicAuthHelper('http_auth_2')
        self.pas.plugins.activatePlugin(IExtractionPlugin, 'http_auth_2')

        # Extract, we should see cache misses
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(2, 2, 0)

        # Extract again, we should see cache hits
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(2, 2, 2)

        # Extract yet again, we should see more hits
        self.pas._extractUserIds(request, self.pas.plugins)
        self.assertCacheStats(2, 2, 4)

    def test__findUser(self):
        # Find, we should see a cache miss
        self.pas._findUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 0)

        # Find again, we should see a cache hit
        self.pas._findUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 1)

        # Find yet again, we should see another hit
        self.pas._findUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 2)

    def test__verifyUser(self):
        # Verify, we should see a cache miss
        self.pas._verifyUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 0)

        # Verify again, we should see a cache hit
        self.pas._verifyUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 1)

        # Verify yet again, we should see another hit
        self.pas._verifyUser(self.pas.plugins, pastc.user_name)
        self.assertCacheStats(1, 1, 2)

    def test_getUser(self):
        self.pas.getUser(pastc.user_name)
        self.assertCacheStats(2, 2, 0)

        self.pas.getUser(pastc.user_name)
        self.assertCacheStats(2, 2, 2)

        self.pas.getUser(pastc.user_name)
        self.assertCacheStats(2, 2, 4)

    def test_getUserById(self):
        self.pas.getUserById(pastc.user_name)
        self.assertCacheStats(2, 2, 0)

        self.pas.getUserById(pastc.user_name)
        self.assertCacheStats(2, 2, 2)

        self.pas.getUserById(pastc.user_name)
        self.assertCacheStats(2, 2, 4)

    def test_validate(self):
        # Rig the request so it looks like we traversed to doc
        request = self.app.REQUEST
        request['PUBLISHED'] = self.doc
        request['PARENTS'] = [self.app, self.folder]
        request.steps = list(self.doc.getPhysicalPath())
        request._auth = 'Basic %s' % pastc.user_auth

        user = self.pas.validate(request)
        self.failIf(user is None)
        self.assertEqual(user.getId(), pastc.user_name)
        self.assertEqual(user.getRoles(), ['Authenticated', pastc.user_role])

        self.assertCacheStats(2, 2, 0)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 2)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 4)

    def test_validate_anonymous(self):
        # Rig the request so it looks like we traversed to doc
        request = self.app.REQUEST
        request['PUBLISHED'] = self.doc
        request['PARENTS'] = [self.app, self.folder]
        request.steps = list(self.doc.getPhysicalPath())

        user = self.pas.validate(request)
        self.failUnless(user is None)

        self.assertCacheStats(0, 0, 0)

    def test_validate_utf8_credentials(self):
        # Rig the request so it looks like we traversed to doc
        request = self.app.REQUEST
        request['PUBLISHED'] = self.doc
        request['PARENTS'] = [self.app, self.folder]
        request.steps = list(self.doc.getPhysicalPath())

        # Rig the extractor so it returns UTF-8 credentials
        self.pas.http_auth.extractCredentials = \
            lambda req: { 'login': pastc.user_name
                        , 'password': pastc.user_password
                        , 'extra': 'M\303\244dchen'
                        }

        user = self.pas.validate(request)
        self.failIf(user is None)
        self.assertEqual(user.getId(), pastc.user_name)
        self.assertEqual(user.getRoles(), ['Authenticated', pastc.user_role])

        self.assertCacheStats(2, 2, 0)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 2)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 4)

    def test_validate_unicode_credentials(self):
        # Rig the request so it looks like we traversed to doc
        request = self.app.REQUEST
        request['PUBLISHED'] = self.doc
        request['PARENTS'] = [self.app, self.folder]
        request.steps = list(self.doc.getPhysicalPath())

        # Rig the extractor so it returns Unicode credentials
        self.pas.http_auth.extractCredentials = \
            lambda req: { 'login': pastc.user_name
                        , 'password': pastc.user_password
                        , 'extra': u'M\344dchen'
                        }

        user = self.pas.validate(request)
        self.failIf(user is None)
        self.assertEqual(user.getId(), pastc.user_name)
        self.assertEqual(user.getRoles(), ['Authenticated', pastc.user_role])

        self.assertCacheStats(2, 2, 0)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 2)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 4)

    def test_validate_utf16_credentials(self):
        # Rig the request so it looks like we traversed to doc
        request = self.app.REQUEST
        request['PUBLISHED'] = self.doc
        request['PARENTS'] = [self.app, self.folder]
        request.steps = list(self.doc.getPhysicalPath())

        # Rig the extractor so it returns UTF-16 credentials
        self.pas.http_auth.extractCredentials = \
            lambda req: { 'login': pastc.user_name
                        , 'password': pastc.user_password
                        , 'extra': u'M\344dchen'.encode('utf-16')
                        }

        user = self.pas.validate(request)
        self.failIf(user is None)
        self.assertEqual(user.getId(), pastc.user_name)
        self.assertEqual(user.getRoles(), ['Authenticated', pastc.user_role])

        self.assertCacheStats(2, 2, 0)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 2)

        self.pas.validate(request)
        self.assertCacheStats(2, 2, 4)

    def test__doAddUser(self):
        user_id = 'test_user_2_'
        password = 'secret'

        self.assertCacheStats(0, 0, 0)

        self.pas._doAddUser(user_id, password, [pastc.user_role], [])

        # XXX: _doAddUser calls getUser
        self.assertCacheStats(2, 2, 0)

        # XXX: As a result the user is now cached, but without roles
        user = self.pas.getUserById(user_id)
        self.failIf(user is None)
        self.assertEqual(user.getId(), user_id)
        self.assertEqual(user.getRoles(), ['Authenticated'])

        # XXX: Must clear cache to get roles
        self.pas.ZCacheable_invalidate()

        user = self.pas.getUserById(user_id)
        self.failIf(user is None)
        self.assertEqual(user.getId(), user_id)
        self.assertEqual(user.getRoles(), ['Authenticated', pastc.user_role])


def test_suite():
    from unittest import TestSuite, makeSuite
    return TestSuite((
        makeSuite(CachingTests),
    ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
