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
        _ITEMS = (('foo', 'bar'),)
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar'),
                         {'keywords': hashed})

    def test_createKeywords_multiple(self):
        _ITEMS = (('foo', 'bar'), ('baz', 'peng'))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar', baz='peng'),
                         {'keywords': hashed})

    def test_createKeywords_latin1_umlaut(self):
        _ITEMS = (('foo', 'bar'), ('baz', 'M\344dchen'))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar', baz='M\344dchen'),
                         {'keywords': hashed})

    def test_createKeywords_utf8_umlaut(self):
        _ITEMS = (('foo', 'bar'), ('baz', 'M\303\244dchen'))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar', baz='M\303\244dchen'),
                         {'keywords': hashed})

    def test_createKeywords_unicode_umlaut(self):
        _ITEMS = (('foo', 'bar'), ('baz', u'M\344dchen'))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar', baz=u'M\344dchen'),
                         {'keywords': hashed})

    def test_createKeywords_utf16_umlaut(self):
        _ITEMS = (('foo', 'bar'), ('baz', u'M\344dchen'.encode('utf-16')))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar',
                                        baz=u'M\344dchen'.encode('utf-16')),
                         {'keywords': hashed})

    def test_createKeywords_unicode_chinese(self):
        _ITEMS = (('foo', 'bar'), ('baz', u'\u03a4\u03b6'))
        hashed = _createHashedValue(_ITEMS)
        self.assertEqual(createKeywords(foo='bar', baz=u'\u03a4\u03b6'),
                {'keywords': hashed})

def _createHashedValue(items):
    import sha
    hasher = sha.new()
    items = list(items)
    items.sort()
    for k, v in items:
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        hasher.update(k)
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        hasher.update(v)
    return hasher.hexdigest()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(UtilityTests),
    ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
