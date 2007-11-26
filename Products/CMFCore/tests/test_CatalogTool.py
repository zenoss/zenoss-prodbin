##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit tests for CatalogTool module.

$Id: test_CatalogTool.py 66324 2006-04-02 21:13:25Z yuppie $
"""

import unittest
import Testing
import Zope2
Zope2.startup()

from AccessControl.SecurityManagement import newSecurityManager
from DateTime import DateTime

from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.security import OmnipotentUser
from Products.CMFCore.tests.base.security import UserWithRoles
from Products.CMFCore.tests.base.testcase import SecurityTest


class IndexableObjectWrapperTests(unittest.TestCase):

    def _getTargetClass(self):
        from Products.CMFCore.CatalogTool import IndexableObjectWrapper

        return IndexableObjectWrapper

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.portal_catalog \
                import IndexableObjectWrapper as IIndexableObjectWrapper

        verifyClass(IIndexableObjectWrapper, self._getTargetClass())

    def test_z3interfaces(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IIndexableObjectWrapper

        verifyClass(IIndexableObjectWrapper, self._getTargetClass())

    def test_allowedRolesAndUsers(self):
        obj = DummyContent()
        w = self._makeOne({}, obj)
        self.assertEqual(w.allowedRolesAndUsers(), ['Manager'])

    def test___str__(self):
        obj = DummyContent('foo')
        w = self._makeOne({}, obj)
        self.assertEqual(str(w), str(obj))

    def test_proxied_attributes(self):
        obj = DummyContent('foo')
        obj.title = 'Foo'
        w = self._makeOne({}, obj)
        self.assertEqual(w.getId(), 'foo')
        self.assertEqual(w.Title(), 'Foo')

    def test_vars(self):
        obj = DummyContent()
        w = self._makeOne({'bar': 1, 'baz': 2}, obj)
        self.assertEqual(w.bar, 1)
        self.assertEqual(w.baz, 2)

    def test_provided(self):
        from Products.CMFCore.interfaces import IContentish
        from Products.CMFCore.interfaces import IIndexableObjectWrapper

        obj = DummyContent()
        w = self._makeOne({}, obj)
        self.failUnless(IContentish.providedBy(w))
        self.failUnless(IIndexableObjectWrapper.providedBy(w))


class CatalogToolTests(SecurityTest):

    def _getTargetClass(self):
        from Products.CMFCore.CatalogTool import CatalogTool

        return CatalogTool

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.interfaces.portal_actions \
                import ActionProvider as IActionProvider
        from Products.CMFCore.interfaces.portal_catalog \
                import portal_catalog as ICatalogTool
        from Products.ZCatalog.IZCatalog import IZCatalog

        verifyClass(IActionProvider, self._getTargetClass())
        verifyClass(ICatalogTool, self._getTargetClass())
        verifyClass(IZCatalog, self._getTargetClass())

    def test_z3interfaces(self):
        from zope.interface.verify import verifyClass
        from Products.CMFCore.interfaces import IActionProvider
        from Products.CMFCore.interfaces import ICatalogTool
        from Products.ZCatalog.interfaces import IZCatalog

        verifyClass(IActionProvider, self._getTargetClass())
        verifyClass(ICatalogTool, self._getTargetClass())
        verifyClass(IZCatalog, self._getTargetClass())

    def loginWithRoles(self, *roles):
        user = UserWithRoles(*roles).__of__(self.root)
        newSecurityManager(None, user)

    def loginManager(self):
        user = OmnipotentUser().__of__(self.root)
        newSecurityManager(None, user)

    def test_processActions(self):
        """
            Tracker #405:  CatalogTool doesn't accept optional third
            argument, 'idxs', to 'catalog_object'.
        """
        tool = self._makeOne()
        dummy = DummyContent(catalog=1)

        tool.catalog_object( dummy, '/dummy' )
        tool.catalog_object( dummy, '/dummy', [ 'SearchableText' ] )

    def test_search_anonymous(self):
        catalog = self._makeOne()
        dummy = DummyContent(catalog=1)
        catalog.catalog_object(dummy, '/dummy')

        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(0, len(catalog.searchResults()))

    def test_search_inactive(self):
        catalog = self._makeOne()
        now = DateTime()
        dummy = DummyContent(catalog=1)
        dummy._View_Permission = ('Blob',)

        self.loginWithRoles('Blob')

        # not yet effective
        dummy.effective = now+1
        dummy.expires = now+2
        catalog.catalog_object(dummy, '/dummy')
        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(0, len(catalog.searchResults()))

        # already expired
        dummy.effective = now-2
        dummy.expires = now-1
        catalog.catalog_object(dummy, '/dummy')
        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(0, len(catalog.searchResults()))

    def test_search_restrict_manager(self):
        catalog = self._makeOne()
        now = DateTime()
        dummy = DummyContent(catalog=1)

        self.loginManager()

        # already expired
        dummy.effective = now-4
        dummy.expires = now-2
        catalog.catalog_object(dummy, '/dummy')
        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(1, len(catalog.searchResults()))

        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-1, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-1, 'range': 'max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': (now-3, now-1), 'range': 'min:max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': (now-3, now-1), 'range': 'minmax'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-2})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-2, 'range': None})))

    def test_search_restrict_inactive(self):
        catalog = self._makeOne()
        now = DateTime()
        dummy = DummyContent(catalog=1)
        dummy._View_Permission = ('Blob',)

        self.loginWithRoles('Blob')

        # already expired
        dummy.effective = now-4
        dummy.expires = now-2
        catalog.catalog_object(dummy, '/dummy')
        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(0, len(catalog.searchResults()))

        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now+3, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now+3, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': (now-3, now-1), 'range': 'min:max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': (now-3, now-1), 'range': 'minmax'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-2, 'range': None})))

    def test_search_restrict_visible(self):
        catalog = self._makeOne()
        now = DateTime()
        dummy = DummyContent(catalog=1)
        dummy._View_Permission = ('Blob',)

        self.loginWithRoles('Blob')

        # visible
        dummy.effective = now-2
        dummy.expires = now+2
        catalog.catalog_object(dummy, '/dummy')
        self.assertEqual(1, len(catalog._catalog.searchResults()))
        self.assertEqual(1, len(catalog.searchResults()))

        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': now-1, 'range': 'min'})))
        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': now-1, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': now+1, 'range': 'min'})))
        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': now+1, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': (now-1, now+1), 'range': 'min:max'})))
        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': (now-1, now+1), 'range': 'minmax'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-2, 'range': None})))

        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': now-3, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': now-3, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': now+3, 'range': 'min'})))
        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': now+3, 'range': 'max'})))
        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': (now-3, now+3), 'range': 'min:max'})))
        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': (now-3, now+3), 'range': 'minmax'})))

        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-1, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-1, 'range': 'max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now+1, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now+1, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': (now-1, now+1), 'range': 'min:max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': (now-1, now+1), 'range': 'minmax'})))

        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'min'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now-3, 'range': 'max'})))
        self.assertEqual(0, len(catalog.searchResults(
            expires={'query': now+3, 'range': 'min'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': now+3, 'range': 'max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': (now-3, now+3), 'range': 'min:max'})))
        self.assertEqual(1, len(catalog.searchResults(
            expires={'query': (now-3, now+3), 'range': 'minmax'})))

        self.assertEqual(1, len(catalog.searchResults(
            effective={'query': now-1, 'range': 'max'},
            expires={'query': now+1, 'range': 'min'})))

        self.assertEqual(0, len(catalog.searchResults(
            effective={'query': now+1, 'range': 'max'},
            expires={'query': now+3, 'range': 'min'})))

    def test_convertQuery(self):
        convert = self._makeOne()._convertQuery

        kw = {}
        convert(kw)
        self.assertEqual(kw, {})

        kw = {'expires': 5, 'expires_usage': 'brrr:min'}
        self.assertRaises(ValueError, convert, kw)

        kw = {'foo': 'bar'}
        convert(kw)
        self.assertEqual(kw, {'foo': 'bar'})

        kw = {'expires': 5, 'expires_usage': 'range:min'}
        convert(kw)
        self.assertEqual(kw, {'expires': {'query': 5, 'range': 'min'}})

        kw = {'expires': 5, 'expires_usage': 'range:max'}
        convert(kw)
        self.assertEqual(kw, {'expires': {'query': 5, 'range': 'max'}})

        kw = {'expires': (5,7), 'expires_usage': 'range:min:max'}
        convert(kw)
        self.assertEqual(kw, {'expires': {'query': (5,7), 'range': 'min:max'}})

    def test_refreshCatalog(self):
        site = DummySite('site').__of__(self.root)
        site._setObject('dummy', DummyContent(catalog=1))
        site._setObject('portal_catalog', self._makeOne())
        ctool = site.portal_catalog
        ctool.catalog_object(site.dummy, '/dummy')

        self.assertEqual(1, len(ctool._catalog.searchResults()))
        ctool.refreshCatalog(clear=1)
        self.assertEqual(1, len(ctool._catalog.searchResults()),
                         'CMF Collector issue #379 (\'Update Catalog\' '
                         'fails): %s entries after refreshCatalog'
                         % (len(ctool._catalog.searchResults()),))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(IndexableObjectWrapperTests),
        unittest.makeSuite(CatalogToolTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
