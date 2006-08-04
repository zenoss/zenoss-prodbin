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
""" Unit tests for ContentTypeRegistry module.

$Id: test_ContentTypeRegistry.py 38418 2005-09-09 08:40:13Z yuppie $
"""

from unittest import TestCase, TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()


class MajorMinorPredicateTests( TestCase ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ContentTypeRegistry import MajorMinorPredicate

        return MajorMinorPredicate(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ContentTypeRegistry import MajorMinorPredicate
        from Products.CMFCore.interfaces.ContentTypeRegistry \
                import ContentTypeRegistryPredicate \
                as IContentTypeRegistryPredicate

        verifyClass(IContentTypeRegistryPredicate, MajorMinorPredicate)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces \
                    import IContentTypeRegistryPredicate
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ContentTypeRegistry import MajorMinorPredicate

        verifyClass(IContentTypeRegistryPredicate, MajorMinorPredicate)

    def test_empty( self ):
        pred = self._makeOne('empty')
        assert pred.getMajorType() == 'None'
        assert pred.getMinorType() == 'None'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )

    def test_simple( self ):
        pred = self._makeOne('plaintext')
        pred.edit( 'text', 'plain' )
        assert pred.getMajorType() == 'text'
        assert pred.getMinorType() == 'plain'
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo', 'text/html', 'asdfljksadf' )
        assert not pred( '', '', '' )
        assert not pred( '', 'asdf', '' )

    def test_wildcard( self ):
        pred = self._makeOne('alltext')
        pred.edit( 'text', '' )
        assert pred.getMajorType() == 'text'
        assert pred.getMinorType() == ''
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo', 'text/html', 'asdfljksadf' )
        assert not pred( 'foo', 'image/png', 'asdfljksadf' )

        pred.edit( '', 'html' )
        assert pred.getMajorType() == ''
        assert pred.getMinorType() == 'html'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo', 'text/html', 'asdfljksadf' )
        assert not pred( 'foo', 'image/png', 'asdfljksadf' )


class ExtensionPredicateTests( TestCase ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ContentTypeRegistry import ExtensionPredicate

        return ExtensionPredicate(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ContentTypeRegistry import ExtensionPredicate
        from Products.CMFCore.interfaces.ContentTypeRegistry \
                import ContentTypeRegistryPredicate \
                as IContentTypeRegistryPredicate

        verifyClass(IContentTypeRegistryPredicate, ExtensionPredicate)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces \
                    import IContentTypeRegistryPredicate
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ContentTypeRegistry import ExtensionPredicate

        verifyClass(IContentTypeRegistryPredicate, ExtensionPredicate)

    def test_empty( self ):
        pred = self._makeOne('empty')
        assert pred.getExtensions() == 'None'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo.txt', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo.bar', 'text/html', 'asdfljksadf' )

    def test_simple( self ):
        pred = self._makeOne('stardottext')
        pred.edit( 'txt' )
        assert pred.getExtensions() == 'txt'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo.txt', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo.bar', 'text/html', 'asdfljksadf' )

    def test_multi( self ):
        pred = self._makeOne('stardottext')
        pred.edit( 'txt text html htm' )
        assert pred.getExtensions() == 'txt text html htm'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo.txt', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo.text', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo.html', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo.htm', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo.bar', 'text/html', 'asdfljksadf' )


class MimeTypeRegexPredicateTests( TestCase ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ContentTypeRegistry \
                import MimeTypeRegexPredicate

        return MimeTypeRegexPredicate(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ContentTypeRegistry \
                import MimeTypeRegexPredicate
        from Products.CMFCore.interfaces.ContentTypeRegistry \
                import ContentTypeRegistryPredicate \
                as IContentTypeRegistryPredicate

        verifyClass(IContentTypeRegistryPredicate, MimeTypeRegexPredicate)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces \
                    import IContentTypeRegistryPredicate
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ContentTypeRegistry \
                import MimeTypeRegexPredicate

        verifyClass(IContentTypeRegistryPredicate, MimeTypeRegexPredicate)

    def test_empty( self ):
        pred = self._makeOne('empty')
        assert pred.getPatternStr() == 'None'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )

    def test_simple( self ):
        pred = self._makeOne('plaintext')
        pred.edit( 'text/plain' )
        assert pred.getPatternStr() == 'text/plain'
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'foo', 'text/html', 'asdfljksadf' )

    def test_pattern( self ):
        pred = self._makeOne('alltext')
        pred.edit( 'text/*' )
        assert pred.getPatternStr() == 'text/*'
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'foo', 'text/html', 'asdfljksadf' )
        assert not pred( 'foo', 'image/png', 'asdfljksadf' )


class NameRegexPredicateTests( TestCase ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ContentTypeRegistry import NameRegexPredicate

        return NameRegexPredicate(*args, **kw)

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ContentTypeRegistry import NameRegexPredicate
        from Products.CMFCore.interfaces.ContentTypeRegistry \
                import ContentTypeRegistryPredicate \
                as IContentTypeRegistryPredicate

        verifyClass(IContentTypeRegistryPredicate, NameRegexPredicate)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces \
                    import IContentTypeRegistryPredicate
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ContentTypeRegistry import NameRegexPredicate

        verifyClass(IContentTypeRegistryPredicate, NameRegexPredicate)

    def test_empty( self ):
        pred = self._makeOne('empty')
        assert pred.getPatternStr() == 'None'
        assert not pred( 'foo', 'text/plain', 'asdfljksadf' )

    def test_simple( self ):
        pred = self._makeOne('onlyfoo')
        pred.edit( 'foo' )
        assert pred.getPatternStr() == 'foo'
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'fargo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'bar', 'text/plain', 'asdfljksadf' )

    def test_pattern( self ):
        pred = self._makeOne('allfwords')
        pred.edit( 'f.*' )
        assert pred.getPatternStr() == 'f.*'
        assert pred( 'foo', 'text/plain', 'asdfljksadf' )
        assert pred( 'fargo', 'text/plain', 'asdfljksadf' )
        assert not pred( 'bar', 'text/plain', 'asdfljksadf' )


class ContentTypeRegistryTests( TestCase ):

    def _makeOne(self, *args, **kw):
        from Products.CMFCore.ContentTypeRegistry import ContentTypeRegistry

        return ContentTypeRegistry(*args, **kw)

    def setUp( self ):
        self.reg = self._makeOne()

    def test_z2interfaces(self):
        from Interface.Verify import verifyClass
        from Products.CMFCore.ContentTypeRegistry import ContentTypeRegistry
        from Products.CMFCore.interfaces.ContentTypeRegistry \
                import ContentTypeRegistry as IContentTypeRegistry

        verifyClass(IContentTypeRegistry, ContentTypeRegistry)

    def test_z3interfaces(self):
        try:
            from zope.interface.verify import verifyClass
            from Products.CMFCore.interfaces import IContentTypeRegistry
        except ImportError:
            # BBB: for Zope 2.7
            return
        from Products.CMFCore.ContentTypeRegistry import ContentTypeRegistry

        verifyClass(IContentTypeRegistry, ContentTypeRegistry)

    def test_empty( self ):
        reg=self.reg
        assert reg.findTypeName( 'foo', 'text/plain', 'asdfljksadf' ) is None
        assert reg.findTypeName( 'fargo', 'text/plain', 'asdfljksadf' ) is None
        assert reg.findTypeName( 'bar', 'text/plain', 'asdfljksadf' ) is None
        assert not reg.listPredicates()
        self.assertRaises( KeyError, reg.removePredicate, 'xyzzy' )

    def test_reorder( self ):
        reg=self.reg
        predIDs = ( 'foo', 'bar', 'baz', 'qux' )
        for predID in predIDs:
            reg.addPredicate( predID, 'name_regex' )
        ids = tuple( map( lambda x: x[0], reg.listPredicates() ) )
        assert ids == predIDs
        reg.reorderPredicate( 'bar', 3 )
        ids = tuple( map( lambda x: x[0], reg.listPredicates() ) )
        assert ids == ( 'foo', 'baz', 'qux', 'bar' )

    def test_lookup( self ):
        reg=self.reg
        reg.addPredicate( 'image', 'major_minor' )
        reg.getPredicate( 'image' ).edit( 'image', '' )
        reg.addPredicate( 'onlyfoo', 'name_regex' )
        reg.getPredicate( 'onlyfoo' ).edit( 'foo' )
        reg.assignTypeName( 'onlyfoo', 'Foo' )
        assert reg.findTypeName( 'foo', 'text/plain', 'asdfljksadf' ) == 'Foo'
        assert not reg.findTypeName( 'fargo', 'text/plain', 'asdfljksadf' )
        assert not reg.findTypeName( 'bar', 'text/plain', 'asdfljksadf' )
        assert reg.findTypeName( 'foo', '', '' ) == 'Foo'
        assert reg.findTypeName( 'foo', None, None ) == 'Foo'


def test_suite():
    return TestSuite((
        makeSuite( MajorMinorPredicateTests ),
        makeSuite( ExtensionPredicateTests ),
        makeSuite( MimeTypeRegexPredicateTests ),
        makeSuite( NameRegexPredicateTests ),
        makeSuite( ContentTypeRegistryTests ),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
