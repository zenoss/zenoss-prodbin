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
"""ZCTextIndex export / import support unit tests.

$Id: test_exportimport.py 68186 2006-05-19 11:27:24Z yuppie $
"""

import unittest
import Testing

from Acquisition import Implicit

from Products.Five import zcml
from Products.GenericSetup.testing import NodeAdapterTestCase

_PLEXICON_XML = """\
<object name="foo_plexicon" meta_type="ZCTextIndex Lexicon">
 <element name="Whitespace splitter" group="Word Splitter"/>
 <element name="Case Normalizer" group="Case Normalizer"/>
 <element name="Remove listed stop words only" group="Stop Words"/>
</object>
"""

_ZCTEXT_XML = """\
<index name="foo_zctext" meta_type="ZCTextIndex">
 <indexed_attr value="foo_zctext"/>
 <indexed_attr value="baz_zctext"/>
 <extra name="index_type" value="Okapi BM25 Rank"/>
 <extra name="lexicon_id" value="foo_plexicon"/>
</index>
"""


class _extra:

    pass


class DummyCatalog(Implicit):

    pass


class ZCLexiconNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.ZCTextIndex.exportimport \
                import ZCLexiconNodeAdapter

        return ZCLexiconNodeAdapter

    def _populate(self, obj):
        from Products.ZCTextIndex.Lexicon import CaseNormalizer
        from Products.ZCTextIndex.Lexicon import Splitter
        from Products.ZCTextIndex.Lexicon import StopWordRemover
        obj._pipeline = (Splitter(), CaseNormalizer(), StopWordRemover())

    def setUp(self):
        import Products.GenericSetup.ZCTextIndex
        from Products.ZCTextIndex.ZCTextIndex import PLexicon

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCTextIndex)

        self._obj = PLexicon('foo_plexicon')
        self._XML = _PLEXICON_XML


class ZCTextIndexNodeAdapterTests(NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.ZCTextIndex.exportimport \
                import ZCTextIndexNodeAdapter

        return ZCTextIndexNodeAdapter

    def _populate(self, obj):
        obj._indexed_attrs = ['foo_zctext', 'baz_zctext']

    def setUp(self):
        import Products.GenericSetup.ZCTextIndex
        from Products.ZCTextIndex.ZCTextIndex import PLexicon
        from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex

        NodeAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.GenericSetup.ZCTextIndex)

        catalog = DummyCatalog()
        catalog.foo_plexicon = PLexicon('foo_plexicon')
        extra = _extra()
        extra.lexicon_id = 'foo_plexicon'
        extra.index_type='Okapi BM25 Rank'
        self._obj = ZCTextIndex('foo_zctext', extra=extra,
                                caller=catalog).__of__(catalog)
        self._XML = _ZCTEXT_XML


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(ZCLexiconNodeAdapterTests),
        unittest.makeSuite(ZCTextIndexNodeAdapterTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
