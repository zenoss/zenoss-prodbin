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

$Id: test_CatalogTool.py 38418 2005-09-09 08:40:13Z yuppie $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from AccessControl.SecurityManagement import newSecurityManager
from DateTime import DateTime

from Products.CMFCore.tests.base.dummy import DummyContent
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.security import OmnipotentUser
from Products.CMFCore.tests.base.security import UserWithRoles
from Products.CMFCore.tests.base.testcase import SecurityTest


class IndexableObjectWrapperTests(TestCase):

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.CatalogTool import IndexableObjectWrapper
        from Products.CMFCore.interfaces.portal_catalog \
                import IndexableObjectWrapper as IIndexableObjectWrapper

        verifyClass(IIndexableObjectWrapper, IndexableObjectWrapper)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IIndexableObjectWrapper
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.CatalogTool import IndexableObjectWrapper

        verifyClass(IIndexableObjectWrapper, IndexableObjectWrapper)


class CatalogToolTests(SecurityTest):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.CatalogTool import CatalogTool

        return CatalogTool(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.CatalogTool import CatalogTool
        from Products.CMFCore.interfaces.portal_actions \
                import ActionProvider as IActionProvider
        from Products.CMFCore.interfaces.portal_catalog \
                import portal_catalog as ICatalogTool
        from Products.ZCatalog.IZCatalog import IZCatalog

        verifyClass(IActionProvider, CatalogTool)
        verifyClass(ICatalogTool, CatalogTool)
        verifyClass(IZCatalog, CatalogTool)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IActionProvider
            from Products.CMFCore.interfaces import ICatalogTool
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.CatalogTool import CatalogTool

        verifyClass(IActionProvider, CatalogTool)
        verifyClass(ICatalogTool, CatalogTool)

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
    return TestSuite((
        makeSuite(IndexableObjectWrapperTests),
        makeSuite(CatalogToolTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
