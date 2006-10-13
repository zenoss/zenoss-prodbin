##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" GenericSetup.utils unit tests

$Id: test_utils.py 41591 2006-02-10 15:52:17Z yuppie $
"""

import unittest
import Testing

from xml.dom.minidom import parseString

from Products.GenericSetup.utils import PrettyDocument
from Products.GenericSetup.testing import DummySetupEnviron


_EMPTY_PROPERTY_EXPORT = """\
<?xml version="1.0"?>
<dummy>
 <property name="foo_boolean" type="boolean">False</property>
 <property name="foo_date" type="date">1970/01/01</property>
 <property name="foo_float" type="float">0.0</property>
 <property name="foo_int" type="int">0</property>
 <property name="foo_lines" type="lines"/>
 <property name="foo_long" type="long">0</property>
 <property name="foo_string" type="string"></property>
 <property name="foo_text" type="text"></property>
 <property name="foo_tokens" type="tokens"/>
 <property name="foo_selection" select_variable="foobarbaz"
    type="selection"></property>
 <property name="foo_mselection" select_variable="foobarbaz"
    type="multiple selection"/>
 <property name="foo_boolean0" type="boolean">False</property>
 <property name="foo_int_nodel">0</property>
 <property name="foo_float_nodel">0.0</property>
 <property name="foo_boolean_nodel">False</property>
</dummy>
"""

_NORMAL_PROPERTY_EXPORT = """\
<?xml version="1.0"?>
<dummy>
 <property name="foo_boolean" type="boolean">True</property>
 <property name="foo_date" type="date">2000/01/01</property>
 <property name="foo_float" type="float">1.1</property>
 <property name="foo_int" type="int">1</property>
 <property name="foo_lines" type="lines">
  <element value="Foo"/>
  <element value="Lines"/>
 </property>
 <property name="foo_long" type="long">1</property>
 <property name="foo_string" type="string">Foo String</property>
 <property name="foo_text" type="text">Foo
  Text</property>
 <property name="foo_tokens" type="tokens">
  <element value="Foo"/>
  <element value="Tokens"/>
 </property>
 <property name="foo_selection" select_variable="foobarbaz"
    type="selection">Foo</property>
 <property name="foo_mselection" select_variable="foobarbaz"
    type="multiple selection">
  <element value="Foo"/>
  <element value="Baz"/>
 </property>
 <property name="foo_boolean0" type="boolean">False</property>
 <property name="foo_int_nodel">1789</property>
 <property name="foo_float_nodel">3.1415</property>
 <property name="foo_boolean_nodel">True</property>
</dummy>
"""

_FIXED_PROPERTY_EXPORT = """\
<?xml version="1.0"?>
<dummy>
 <property name="foo_boolean">True</property>
 <property name="foo_date">2000/01/01</property>
 <property name="foo_float">1.1</property>
 <property name="foo_int">1</property>
 <property name="foo_lines">
  <element value="Foo"/>
  <element value="Lines"/>
 </property>
 <property name="foo_long">1</property>
 <property name="foo_string">Foo String</property>
 <property name="foo_text">Foo
  Text</property>
 <property name="foo_tokens">
  <element value="Foo"/>
  <element value="Tokens"/></property>
 <property name="foo_selection" type="selection"
    select_variable="foobarbaz">Foo</property>
 <property name="foo_mselection">
  <element value="Foo"/>
  <element value="Baz"/>
 </property>
 <property name="foo_boolean0">False</property>
 <property name="foo_int_nodel">1789</property>
 <property name="foo_float_nodel">3.1415</property>
 <property name="foo_boolean_nodel">True</property>
</dummy>
"""

_SPECIAL_IMPORT = """\
<?xml version="1.0"?>
<dummy>
 <!-- ignore comment, import 0 as False -->
 <property name="foo_boolean0" type="boolean">0</property>
</dummy>
"""

_I18N_IMPORT = """\
<?xml version="1.0"?>
<dummy xmlns:i18n="http://xml.zope.org/namespaces/i18n"
   i18n:domain="dummy_domain">
 <property name="foo_string" i18n:translate="">Foo String</property>
</dummy>
"""

_NOPURGE_IMPORT = """\
<?xml version="1.0"?>
<dummy>
 <property name="lines1">
  <element value="Foo"/>
  <element value="Bar"/>
 </property>
 <property name="lines2" purge="True">
  <element value="Foo"/>
  <element value="Bar"/>
 </property>
 <property name="lines3" purge="False">
  <element value="Foo"/>
  <element value="Bar"/>
 </property>
</dummy>
"""


def _testFunc( *args, **kw ):

    """ This is a test.

    This is only a test.
    """

_TEST_FUNC_NAME = 'Products.GenericSetup.tests.test_utils._testFunc'

class Whatever:
    pass

_WHATEVER_NAME = 'Products.GenericSetup.tests.test_utils.Whatever'

whatever_inst = Whatever()
whatever_inst.__name__ = 'whatever_inst'

_WHATEVER_INST_NAME = 'Products.GenericSetup.tests.test_utils.whatever_inst'

class UtilsTests( unittest.TestCase ):

    def test__getDottedName_simple( self ):

        from Products.GenericSetup.utils import _getDottedName

        self.assertEqual( _getDottedName( _testFunc ), _TEST_FUNC_NAME )

    def test__getDottedName_string( self ):

        from Products.GenericSetup.utils import _getDottedName

        self.assertEqual( _getDottedName( _TEST_FUNC_NAME ), _TEST_FUNC_NAME )

    def test__getDottedName_unicode( self ):

        from Products.GenericSetup.utils import _getDottedName

        dotted = u'%s' % _TEST_FUNC_NAME
        self.assertEqual( _getDottedName( dotted ), _TEST_FUNC_NAME )
        self.assertEqual( type( _getDottedName( dotted ) ), str )

    def test__getDottedName_class( self ):

        from Products.GenericSetup.utils import _getDottedName

        self.assertEqual( _getDottedName( Whatever ), _WHATEVER_NAME )

    def test__getDottedName_inst( self ):

        from Products.GenericSetup.utils import _getDottedName

        self.assertEqual( _getDottedName( whatever_inst )
                        , _WHATEVER_INST_NAME )

    def test__getDottedName_noname( self ):

        from Products.GenericSetup.utils import _getDottedName

        class Doh:
            pass

        doh = Doh()
        self.assertRaises( ValueError, _getDottedName, doh )


class PropertyManagerHelpersTests(unittest.TestCase):

    def _getTargetClass(self):
        from Products.GenericSetup.utils import PropertyManagerHelpers

        return PropertyManagerHelpers

    def _makeOne(self, *args, **kw):
        from Products.GenericSetup.utils import NodeAdapterBase

        class Foo(self._getTargetClass(), NodeAdapterBase):

            pass

        return Foo(*args, **kw)

    def setUp(self):
        from OFS.PropertyManager import PropertyManager

        obj = PropertyManager('obj')
        obj.foobarbaz = ('Foo', 'Bar', 'Baz')
        obj._properties = ()
        obj.manage_addProperty('foo_boolean', '', 'boolean')
        obj.manage_addProperty('foo_date', '1970/01/01', 'date')
        obj.manage_addProperty('foo_float', '0', 'float')
        obj.manage_addProperty('foo_int', '0', 'int')
        obj.manage_addProperty('foo_lines', '', 'lines')
        obj.manage_addProperty('foo_long', '0', 'long')
        obj.manage_addProperty('foo_string', '', 'string')
        obj.manage_addProperty('foo_text', '', 'text')
        obj.manage_addProperty('foo_tokens', '', 'tokens')
        obj.manage_addProperty('foo_selection', 'foobarbaz', 'selection')
        obj.manage_addProperty('foo_mselection', 'foobarbaz',
                               'multiple selection')
        obj.manage_addProperty('foo_boolean0', '', 'boolean')
        obj.manage_addProperty('foo_ro', '', 'string')
        obj._properties[-1]['mode'] = '' # Read-only, not exported or purged
        obj.manage_addProperty('foo_int_nodel', 0, 'int')
        obj._properties[-1]['mode'] = 'w' # Not deletable
        obj.manage_addProperty('foo_float_nodel', 0, 'float')
        obj._properties[-1]['mode'] = 'w' # Not deletable
        obj.manage_addProperty('foo_boolean_nodel', '', 'boolean')
        obj._properties[-1]['mode'] = 'w' # Not deletable
        self.helpers = self._makeOne(obj, DummySetupEnviron())

    def _populate(self, obj):
        obj._updateProperty('foo_boolean', 'True')
        obj._updateProperty('foo_date', '2000/01/01')
        obj._updateProperty('foo_float', '1.1')
        obj._updateProperty('foo_int', '1')
        obj._updateProperty('foo_lines', 'Foo\nLines')
        obj._updateProperty('foo_long', '1')
        obj._updateProperty('foo_string', 'Foo String')
        obj._updateProperty('foo_text', 'Foo\nText')
        obj._updateProperty( 'foo_tokens', ('Foo', 'Tokens') )
        obj._updateProperty('foo_selection', 'Foo')
        obj._updateProperty( 'foo_mselection', ('Foo', 'Baz') )
        obj.foo_boolean0 = 0
        obj._updateProperty('foo_ro', 'RO')
        obj._updateProperty('foo_int_nodel', '1789')
        obj._updateProperty('foo_float_nodel', '3.1415')
        obj._updateProperty('foo_boolean_nodel', 'True')

    def test__extractProperties_empty(self):
        doc = self.helpers._doc = PrettyDocument()
        node = doc.createElement('dummy')
        node.appendChild(self.helpers._extractProperties())
        doc.appendChild(node)

        self.assertEqual(doc.toprettyxml(' '), _EMPTY_PROPERTY_EXPORT)

    def test__extractProperties_normal(self):
        self._populate(self.helpers.context)
        doc = self.helpers._doc = PrettyDocument()
        node = doc.createElement('dummy')
        node.appendChild(self.helpers._extractProperties())
        doc.appendChild(node)

        self.assertEqual(doc.toprettyxml(' '), _NORMAL_PROPERTY_EXPORT)

    def test__purgeProperties(self):
        obj = self.helpers.context
        self._populate(obj)
        self.helpers._purgeProperties()

        self.assertEqual(getattr(obj, 'foo_boolean', None), None)
        self.assertEqual(getattr(obj, 'foo_date', None), None)
        self.assertEqual(getattr(obj, 'foo_float', None), None)
        self.assertEqual(getattr(obj, 'foo_int', None), None)
        self.assertEqual(getattr(obj, 'foo_lines', None), None)
        self.assertEqual(getattr(obj, 'foo_long', None), None)
        self.assertEqual(getattr(obj, 'foo_string', None), None)
        self.assertEqual(getattr(obj, 'foo_text', None), None)
        self.assertEqual(getattr(obj, 'foo_tokens', None), None)
        self.assertEqual(getattr(obj, 'foo_selection', None), None)
        self.assertEqual(getattr(obj, 'foo_mselection', None), None)
        self.assertEqual(getattr(obj, 'foo_boolean0', None), None)
        self.assertEqual(getattr(obj, 'foo_ro', None), 'RO')

    def test__initProperties_normal(self):
        node = parseString(_NORMAL_PROPERTY_EXPORT).documentElement
        self.helpers._initProperties(node)
        self.assertEqual(type(self.helpers.context.foo_int), int)
        self.assertEqual(type(self.helpers.context.foo_string), str)
        self.assertEqual(type(self.helpers.context.foo_tokens), tuple)
        self.assertEqual(type(self.helpers.context.foo_tokens[0]), str)

        doc = self.helpers._doc = PrettyDocument()
        node = doc.createElement('dummy')
        node.appendChild(self.helpers._extractProperties())
        doc.appendChild(node)

        self.assertEqual(doc.toprettyxml(' '), _NORMAL_PROPERTY_EXPORT)

    def test__initProperties_fixed(self):
        node = parseString(_FIXED_PROPERTY_EXPORT).documentElement
        self.helpers._initProperties(node)

        doc = self.helpers._doc = PrettyDocument()
        node = doc.createElement('dummy')
        node.appendChild(self.helpers._extractProperties())
        doc.appendChild(node)

        self.assertEqual(doc.toprettyxml(' '), _NORMAL_PROPERTY_EXPORT)

    def test__initProperties_special(self):
        node = parseString(_SPECIAL_IMPORT).documentElement
        self.helpers._initProperties(node)

        doc = self.helpers._doc = PrettyDocument()
        node = doc.createElement('dummy')
        node.appendChild(self.helpers._extractProperties())
        doc.appendChild(node)

        self.assertEqual(doc.toprettyxml(' '), _EMPTY_PROPERTY_EXPORT)

    def test__initProperties_i18n(self):
        self.helpers.context.manage_addProperty('i18n_domain', '', 'string')
        node = parseString(_I18N_IMPORT).documentElement
        self.helpers._initProperties(node)

        self.assertEqual(self.helpers.context.i18n_domain, 'dummy_domain')

    def test__initProperties_nopurge_base(self):
        node = parseString(_NOPURGE_IMPORT).documentElement
        self.helpers.environ._should_purge = True # base profile
        obj = self.helpers.context
        obj._properties = ()
        obj.manage_addProperty('lines1', ('Foo', 'Gee'), 'lines')
        obj.manage_addProperty('lines2', ('Foo', 'Gee'), 'lines')
        obj.manage_addProperty('lines3', ('Foo', 'Gee'), 'lines')
        self.helpers._initProperties(node)

        self.assertEquals(obj.lines1, ('Foo', 'Bar'))
        self.assertEquals(obj.lines2, ('Foo', 'Bar'))
        self.assertEquals(obj.lines3, ('Gee', 'Foo', 'Bar'))

    def test__initProperties_nopurge_extension(self):
        node = parseString(_NOPURGE_IMPORT).documentElement
        self.helpers.environ._should_purge = False # extension profile
        obj = self.helpers.context
        obj._properties = ()
        obj.manage_addProperty('lines1', ('Foo', 'Gee'), 'lines')
        obj.manage_addProperty('lines2', ('Foo', 'Gee'), 'lines')
        obj.manage_addProperty('lines3', ('Foo', 'Gee'), 'lines')
        self.helpers._initProperties(node)

        self.assertEquals(obj.lines1, ('Foo', 'Bar'))
        self.assertEquals(obj.lines2, ('Foo', 'Bar'))
        self.assertEquals(obj.lines3, ('Gee', 'Foo', 'Bar'))


class PrettyDocumentTests(unittest.TestCase):

    def test_attr_quoting(self):
        original = 'baz &nbsp;<bar>&"\''
        expected = ('<?xml version="1.0"?>\n'
                    '<doc foo="baz &amp;nbsp;&lt;bar&gt;&amp;&quot;\'"/>\n')

        doc = PrettyDocument()
        node = doc.createElement('doc')
        node.setAttribute('foo', original)
        doc.appendChild(node)
        self.assertEqual(doc.toprettyxml(' '), expected)
        # Reparse
        e = parseString(expected).documentElement
        self.assertEqual(e.getAttribute('foo'), original)

    def test_text_quoting(self):
        original = 'goo &nbsp;<hmm>&"\''
        expected = ('<?xml version="1.0"?>\n'
                    '<doc>goo &amp;nbsp;&lt;hmm&gt;&amp;"\'</doc>\n')

        doc = PrettyDocument()
        node = doc.createElement('doc')
        child = doc.createTextNode(original)
        node.appendChild(child)
        doc.appendChild(node)
        self.assertEqual(doc.toprettyxml(' '), expected)
        # Reparse
        e = parseString(expected).documentElement
        self.assertEqual(e.childNodes[0].nodeValue, original)

def test_suite():
    # reimport to make sure tests are run from Products
    from Products.GenericSetup.tests.test_utils import UtilsTests

    return unittest.TestSuite((
        unittest.makeSuite(UtilsTests),
        unittest.makeSuite(PropertyManagerHelpersTests),
        unittest.makeSuite(PrettyDocumentTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
