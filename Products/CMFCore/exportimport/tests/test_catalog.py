##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Catalog tool setup handler unit tests.

$Id: test_catalog.py 40415 2005-11-29 20:05:50Z yuppie $
"""

import unittest
import Testing
import Zope2
Zope2.startup()

import Products
from OFS.Folder import Folder
from Products.Five import zcml
from Products.ZCTextIndex.Lexicon import CaseNormalizer
from Products.ZCTextIndex.Lexicon import Splitter
from Products.ZCTextIndex.Lexicon import StopWordRemover
from Products.ZCTextIndex.ZCTextIndex import PLexicon

from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.CatalogTool import CatalogTool
from Products.CMFCore.tests.base.testcase import PlacelessSetup

_EMPTY_EXPORT = """\
<?xml version="1.0"?>
<object meta_type="CMF Catalog" name="portal_catalog">
 <property name="title"/>
</object>
"""

_NORMAL_EXPORT = """\
<?xml version="1.0"?>
<object meta_type="CMF Catalog" name="portal_catalog">
 <property name="title"/>
 <object name="foo_plexicon" meta_type="ZCTextIndex Lexicon">
  <element name="Whitespace splitter" group="Word Splitter"/>
  <element name="Case Normalizer" group="Case Normalizer"/>
  <element name="Remove listed stop words only" group="Stop Words"/>
 </object>
 <index name="foo_zctext" meta_type="ZCTextIndex">
  <indexed_attr value="foo_zctext"/>
  <extra name="index_type" value="Okapi BM25 Rank"/>
  <extra name="lexicon_id" value="foo_plexicon"/>
 </index>
 <column value="foo_zctext"/>
</object>
"""

_UPDATE_IMPORT = """\
<?xml version="1.0"?>
<object meta_type="CMF Catalog" name="portal_catalog">
 <index name="foo_date" meta_type="DateIndex">
  <property name="index_naive_time_as_local">True</property>
 </index>
 <column value="foo_date"/>
</object>
"""


class _extra:

    pass


class _CatalogToolSetup(PlacelessSetup, BaseRegistryTests):

    def _initSite(self, foo=2):
        site = self.root.site = Folder(id='site')
        ctool = site.portal_catalog = CatalogTool()

        for obj_id in ctool.objectIds():
            ctool._delObject(obj_id)
        for idx_id in ctool.indexes():
            ctool.delIndex(idx_id)
        for col in ctool.schema()[:]:
            ctool.delColumn(col)

        if foo > 0:
            ctool._setObject('foo_plexicon', PLexicon('foo_plexicon'))
            lex = ctool.foo_plexicon
            lex._pipeline = (Splitter(), CaseNormalizer(), StopWordRemover())

            extra = _extra()
            extra.lexicon_id = 'foo_plexicon'
            extra.index_type = 'Okapi BM25 Rank'
            ctool.addIndex('foo_zctext', 'ZCTextIndex', extra)

            ctool.addColumn('foo_zctext')

        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCatalog)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCTextIndex)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportCatalogToolTests(_CatalogToolSetup):

    def test_unchanged(self):
        from Products.CMFCore.exportimport.catalog import exportCatalogTool

        site = self._initSite(0)
        context = DummyExportContext(site)
        exportCatalogTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'catalog.xml')
        self._compareDOM(text, _EMPTY_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal(self):
        from Products.CMFCore.exportimport.catalog import exportCatalogTool

        site = self._initSite(2)
        context = DummyExportContext(site)
        exportCatalogTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'catalog.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importCatalogToolTests(_CatalogToolSetup):

    def test_empty_purge(self):
        from Products.CMFCore.exportimport.catalog import importCatalogTool

        site = self._initSite(2)
        ctool = site.portal_catalog

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

        context = DummyImportContext(site, True)
        context._files['catalog.xml'] = _EMPTY_EXPORT
        importCatalogTool(context)

        self.assertEqual(len(ctool.objectIds()), 0)
        self.assertEqual(len(ctool.indexes()), 0)
        self.assertEqual(len(ctool.schema()), 0)

    def test_empty_update(self):
        from Products.CMFCore.exportimport.catalog import importCatalogTool

        site = self._initSite(2)
        ctool = site.portal_catalog

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

        context = DummyImportContext(site, False)
        context._files['catalog.xml'] = _EMPTY_EXPORT
        importCatalogTool(context)

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

    def test_normal_purge(self):
        from Products.CMFCore.exportimport.catalog import exportCatalogTool
        from Products.CMFCore.exportimport.catalog import importCatalogTool

        site = self._initSite(2)
        ctool = site.portal_catalog

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

        context = DummyImportContext(site, True)
        context._files['catalog.xml'] = _NORMAL_EXPORT
        importCatalogTool(context)

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

        # complete the roundtrip
        context = DummyExportContext(site)
        exportCatalogTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'catalog.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal_update(self):
        from Products.CMFCore.exportimport.catalog import importCatalogTool

        site = self._initSite(2)
        ctool = site.portal_catalog

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 1)
        self.assertEqual(len(ctool.schema()), 1)

        context = DummyImportContext(site, False)
        context._files['catalog.xml'] = _UPDATE_IMPORT
        importCatalogTool(context)

        self.assertEqual(len(ctool.objectIds()), 1)
        self.assertEqual(len(ctool.indexes()), 2)
        self.assertEqual(len(ctool.schema()), 2)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(exportCatalogToolTests),
        unittest.makeSuite(importCatalogToolTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
