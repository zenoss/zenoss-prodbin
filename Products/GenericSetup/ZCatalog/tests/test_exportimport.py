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
"""ZCatalog export / import support unit tests.

$Id: test_exportimport.py 68488 2006-06-04 17:22:57Z yuppie $
"""

import unittest
from Testing import ZopeTestCase
ZopeTestCase.installProduct('ZCTextIndex', 1)

from Products.Five import zcml
from zope.component import getMultiAdapter

from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.testing import DummySetupEnviron


class _extra:

    pass


_CATALOG_BODY = """\
<?xml version="1.0"?>
<object name="foo_catalog" meta_type="ZCatalog">
 <property name="title"></property>
 <object name="foo_plexicon" meta_type="ZCTextIndex Lexicon">
  <element name="Whitespace splitter" group="Word Splitter"/>
  <element name="Case Normalizer" group="Case Normalizer"/>
  <element name="Remove listed stop words only" group="Stop Words"/>
 </object>
%s <index name="foo_date" meta_type="DateIndex">
  <property name="index_naive_time_as_local">True</property>
 </index>
 <index name="foo_daterange" meta_type="DateRangeIndex" since_field="bar"
    until_field="baz"/>
 <index name="foo_field" meta_type="FieldIndex">
  <indexed_attr value="bar"/>
 </index>
 <index name="foo_keyword" meta_type="KeywordIndex">
  <indexed_attr value="bar"/>
 </index>
 <index name="foo_path" meta_type="PathIndex"/>
%s <index name="foo_topic" meta_type="TopicIndex">
  <filtered_set name="bar" meta_type="PythonFilteredSet" expression="True"/>
  <filtered_set name="baz" meta_type="PythonFilteredSet" expression="False"/>
 </index>
 <index name="foo_zctext" meta_type="ZCTextIndex">
  <indexed_attr value="foo_zctext"/>
  <extra name="index_type" value="Okapi BM25 Rank"/>
  <extra name="lexicon_id" value="foo_plexicon"/>
 </index>
 <column value="eggs"/>
 <column value="spam"/>
</object>
"""

_CATALOG_UPDATE_BODY = """\
<?xml version="1.0"?>
<object name="foo_catalog">
 <object name="foo_vocabulary" remove="True"/>
 <index name="foo_text" remove="True"/>
 <index name="foo_text" meta_type="ZCTextIndex">
  <indexed_attr value="foo_text"/>
  <extra name="index_type" value="Okapi BM25 Rank"/>
  <extra name="lexicon_id" value="foo_plexicon"/>
 </index>
</object>
"""

_TEXT_XML = """\
 <index name="foo_text" meta_type="TextIndex" deprecated="True"/>
"""

_VOCABULARY_XML = """\
 <object name="foo_vocabulary" meta_type="Vocabulary" deprecated="True"/>
"""

_ZCTEXT_XML = """\
 <index name="foo_text" meta_type="ZCTextIndex">
  <indexed_attr value="foo_text"/>
  <extra name="index_type" value="Okapi BM25 Rank"/>
  <extra name="lexicon_id" value="foo_plexicon"/>
 </index>
"""


class ZCatalogXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.ZCatalog.exportimport \
                import ZCatalogXMLAdapter

        return ZCatalogXMLAdapter

    def _populate(self, obj):
        from Products.ZCTextIndex.Lexicon import CaseNormalizer
        from Products.ZCTextIndex.Lexicon import Splitter
        from Products.ZCTextIndex.Lexicon import StopWordRemover
        from Products.ZCTextIndex.ZCTextIndex import PLexicon

        obj._setObject('foo_plexicon', PLexicon('foo_plexicon'))
        lex = obj.foo_plexicon
        lex._pipeline = (Splitter(), CaseNormalizer(), StopWordRemover())

        obj.addIndex('foo_date', 'DateIndex')

        obj.addIndex('foo_daterange', 'DateRangeIndex')
        idx = obj._catalog.getIndex('foo_daterange')
        idx._edit('bar', 'baz')

        obj.addIndex('foo_field', 'FieldIndex')
        idx = obj._catalog.getIndex('foo_field')
        idx.indexed_attrs = ('bar',)

        obj.addIndex('foo_keyword', 'KeywordIndex')
        idx = obj._catalog.getIndex('foo_keyword')
        idx.indexed_attrs = ('bar',)

        obj.addIndex('foo_path', 'PathIndex')

        obj.addIndex('foo_topic', 'TopicIndex')
        idx = obj._catalog.getIndex('foo_topic')
        idx.addFilteredSet('bar', 'PythonFilteredSet', 'True')
        idx.addFilteredSet('baz', 'PythonFilteredSet', 'False')

        extra = _extra()
        extra.lexicon_id = 'foo_plexicon'
        extra.index_type = 'Okapi BM25 Rank'
        obj.addIndex('foo_zctext', 'ZCTextIndex', extra)

        obj.addColumn('spam')
        obj.addColumn('eggs')

    def _populate_special(self, obj):
        from Products.PluginIndexes.TextIndex.Vocabulary import Vocabulary

        self._populate(self._obj)
        obj._setObject('foo_vocabulary', Vocabulary('foo_vocabulary'))
        obj.addIndex('foo_text', 'TextIndex')

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        import Products.GenericSetup.ZCatalog
        import Products.GenericSetup.ZCTextIndex
        from Products.ZCatalog.ZCatalog import ZCatalog

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCatalog)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCTextIndex)

        self._obj = ZCatalog('foo_catalog')
        self._BODY = _CATALOG_BODY % ('', '')

    def test_body_get_special(self):
        self._populate_special(self._obj)
        context = DummySetupEnviron()
        adapted = getMultiAdapter((self._obj, context), IBody)
        self.assertEqual(adapted.body,
                         _CATALOG_BODY % (_VOCABULARY_XML, _TEXT_XML))

    def test_body_set_update(self):
        self._populate_special(self._obj)
        context = DummySetupEnviron()
        context._should_purge = False
        adapted = getMultiAdapter((self._obj, context), IBody)
        adapted.body = _CATALOG_UPDATE_BODY
        self.assertEqual(adapted.body, _CATALOG_BODY % ('', _ZCTEXT_XML))


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(ZCatalogXMLAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
