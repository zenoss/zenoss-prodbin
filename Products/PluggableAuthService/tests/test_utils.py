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

import unittest

from Products.PluggableAuthService.utils import createViewName
from Products.PluggableAuthService.utils import createKeywords


class UtilityTests(unittest.TestCase):

    def test_createViewName(self):
        self.assertEqual(createViewName('foo', 'bar'), 'foo-bar')

    def test_createViewName_no_user_handle(self):
        self.assertEqual(createViewName('foo', None), 'foo')

    def test_createViewName_latin1_umlaut_in_method(self):
        self.assertEqual(createViewName('f\366o'), 'f\366o')

    def test_createViewName_utf8_umlaut_in_method(self):
        self.assertEqual(createViewName('f\303\266o'), 'f\303\266o')

    def test_createViewName_unicode_umlaut_in_method(self):
        self.assertEqual(createViewName(u'f\366o'), 'f\303\266o')

    def test_createViewName_latin1_umlaut_in_handle(self):
        self.assertEqual(createViewName('foo', 'b\344r'), 'foo-b\344r')

    def test_createViewName_utf8_umlaut_in_handle(self):
        self.assertEqual(createViewName('foo', 'b\303\244r'), 'foo-b\303\244r')

    def test_createViewName_unicode_umlaut_in_handle(self):
        self.assertEqual(createViewName('foo', u'b\344r'), 'foo-b\303\244r')

    def test_createKeywords(self):
        self.assertEqual(createKeywords(foo='bar'),
                {'keywords': '8843d7f92416211de9ebb963ff4ce28125932878'})

    def test_createKeywords_multiple(self):
        self.assertEqual(createKeywords(foo='bar', baz='peng'),
                {'keywords': '0237196c9a6c711223d087676671351510c265be'})

    def test_createKeywords_latin1_umlaut(self):
        self.assertEqual(createKeywords(foo='bar', baz='M\344dchen'),
                {'keywords': '1a952e3797b287f60e034c19dacd0eca49c4f437'})

    def test_createKeywords_utf8_umlaut(self):
        self.assertEqual(createKeywords(foo='bar', baz='M\303\244dchen'),
                {'keywords': '62e00b7ef8978f85194632b90e829006b0410472'})

    def test_createKeywords_unicode_umlaut(self):
        self.assertEqual(createKeywords(foo='bar', baz=u'M\344dchen'),
                {'keywords': '62e00b7ef8978f85194632b90e829006b0410472'})

    def test_createKeywords_utf16_umlaut(self):
        self.assertEqual(createKeywords(foo='bar', baz=u'M\344dchen'.encode('utf-16')),
                {'keywords': 'a884c1b0242a14f253e0e361ff1cee808eb18aff'})

    def test_createKeywords_unicode_chinese(self):
        self.assertEqual(createKeywords(foo='bar', baz=u'\u03a4\u03b6'),
                {'keywords': '03b19dff4adbd3b8a2f158456f0f26efe35e1f2c'})


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(UtilityTests),
    ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
