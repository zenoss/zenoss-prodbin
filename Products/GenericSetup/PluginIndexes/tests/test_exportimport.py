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
"""PluginIndexes export / import support unit tests.

$Id: test_exportimport.py 40452 2005-12-01 18:20:45Z yuppie $
"""

import unittest
import Testing

from Products.Five import zcml
from Products.GenericSetup.testing import NodeAdapterTestCase

_DATE_XML = """\
<index name="foo_date" meta_type="DateIndex">
 <property name="index_naive_time_as_local">True</property>
</index>
"""

_DATERANGE_XML = """\
<index name="foo_daterange" meta_type="DateRangeIndex" since_field="bar"
   until_field="baz"/>
"""

_FIELD_XML = """\
<index name="foo_field" meta_type="FieldIndex">
 <indexed_attr value="bar"/>
</index>
"""

_KEYWORD_XML = """\
<index name="foo_keyword" meta_type="KeywordIndex">
 <indexed_attr value="bar"/>
</index>
"""

_PATH_XML = """\
<index name="foo_path" meta_type="PathIndex"/>
"""

_VOCABULARY_XML = """\
<object name="foo_vocabulary" meta_type="Vocabulary" deprecated="True"/>
"""

_TEXT_XML = """\
<index name="foo_text" meta_type="TextIndex" deprecated="True"/>
"""

_SET_XML = """\
<filtered_set name="bar" meta_type="PythonFilteredSet" expression="True"/>
"""

_TOPIC_XML = """\
<index name="foo_topic" meta_type="TopicIndex">
 <filtered_set name="bar" meta_type="PythonFilteredSet" expression="True"/>
 <filtered_set name="baz" meta_type="PythonFilteredSet" expression="False"/>
</index>
"""


class DateIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import DateIndexNodeAdapter

        return DateIndexNodeAdapter

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.DateIndex.DateIndex import DateIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = DateIndex('foo_date')
        self._XML = _DATE_XML


class DateRangeIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import DateRangeIndexNodeAdapter

        return DateRangeIndexNodeAdapter

    def _populate(self, obj):
        obj._edit('bar', 'baz')

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.DateRangeIndex.DateRangeIndex \
                import DateRangeIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = DateRangeIndex('foo_daterange')
        self._XML = _DATERANGE_XML


class FieldIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import PluggableIndexNodeAdapter

        return PluggableIndexNodeAdapter

    def _populate(self, obj):
        obj.indexed_attrs = ('bar',)

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = FieldIndex('foo_field')
        self._XML = _FIELD_XML


class KeywordIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import PluggableIndexNodeAdapter

        return PluggableIndexNodeAdapter

    def _populate(self, obj):
        obj.indexed_attrs = ('bar',)

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.KeywordIndex.KeywordIndex \
                import KeywordIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = KeywordIndex('foo_keyword')
        self._XML = _KEYWORD_XML


class PathIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import PathIndexNodeAdapter

        return PathIndexNodeAdapter

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.PathIndex.PathIndex import PathIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = PathIndex('foo_path')
        self._XML = _PATH_XML


class VocabularyNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import VocabularyNodeAdapter

        return VocabularyNodeAdapter

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.TextIndex.Vocabulary import Vocabulary

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = Vocabulary('foo_vocabulary')
        self._XML = _VOCABULARY_XML

    def test_importNode(self):
        pass


class TextIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import TextIndexNodeAdapter

        return TextIndexNodeAdapter

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.TextIndex.TextIndex import TextIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = TextIndex('foo_text')
        self._XML = _TEXT_XML

    def test_importNode(self):
        pass


class FilteredSetNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import FilteredSetNodeAdapter

        return FilteredSetNodeAdapter

    def _populate(self, obj):
        obj.setExpression('True')

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.TopicIndex.FilteredSet \
                import PythonFilteredSet

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = PythonFilteredSet('bar', '')
        self._XML = _SET_XML


class TopicIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.PluginIndexes.exportimport \
                import TopicIndexNodeAdapter

        return TopicIndexNodeAdapter

    def _populate(self, obj):
        obj.addFilteredSet('bar', 'PythonFilteredSet', 'True')
        obj.addFilteredSet('baz', 'PythonFilteredSet', 'False')

    def setUp(self):
        import Products.GenericSetup.PluginIndexes
        from Products.PluginIndexes.TopicIndex.TopicIndex import TopicIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml',
                         Products.GenericSetup.PluginIndexes)

        self._obj = TopicIndex('foo_topic')
        self._XML = _TOPIC_XML


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(DateIndexNodeAdapterTests),
        unittest.makeSuite(DateRangeIndexNodeAdapterTests),
        unittest.makeSuite(FieldIndexNodeAdapterTests),
        unittest.makeSuite(KeywordIndexNodeAdapterTests),
        unittest.makeSuite(PathIndexNodeAdapterTests),
        unittest.makeSuite(VocabularyNodeAdapterTests),
        unittest.makeSuite(TextIndexNodeAdapterTests),
        unittest.makeSuite(FilteredSetNodeAdapterTests),
        unittest.makeSuite(TopicIndexNodeAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
