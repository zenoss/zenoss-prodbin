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
"""Site properties xml adapter and setup handler unit tests.

$Id: test_properties.py 39963 2005-11-07 19:06:45Z tseaver $
"""

import unittest
import Testing

from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.tests.base.testcase import PlacelessSetup

_PROPERTIES_BODY = """\
<?xml version="1.0"?>
<site>
 <property name="title">Foo</property>
 <property name="foo_string" type="string">foo</property>
 <property name="foo_boolean" type="boolean">False</property>
</site>
"""

_EMPTY_EXPORT = """\
<?xml version="1.0" ?>
<site>
 <property name="title"/>
</site>
"""

_NORMAL_EXPORT = """\
<?xml version="1.0" ?>
<site>
 <property name="title"/>
 <property name="foo" type="string">Foo</property>
 <property name="bar" type="tokens">
  <element value="Bar"/>
 </property>
 <property name="moo" type="tokens">
  <element value="Moo"/>
 </property>
</site>
"""


class PropertiesXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.properties \
                import PropertiesXMLAdapter

        return PropertiesXMLAdapter

    def _populate(self, obj):
        obj._setPropValue('title', 'Foo')
        obj._setProperty('foo_string', 'foo', 'string')
        obj._setProperty('foo_boolean', False, 'boolean')

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.PortalObject import PortalObjectBase

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = PortalObjectBase('foo_site')
        self._BODY = _PROPERTIES_BODY


class _SitePropertiesSetup(PlacelessSetup, BaseRegistryTests):

    def _initSite(self, foo=2, bar=2):
        from Products.CMFCore.PortalObject import PortalObjectBase

        self.root.site = PortalObjectBase('foo_site')
        site = self.root.site

        if foo > 0:
            site._setProperty('foo', '', 'string')
        if foo > 1:
            site._updateProperty('foo', 'Foo')

        if bar > 0:
            site._setProperty( 'bar', (), 'tokens' )
            site._setProperty( 'moo', (), 'tokens' )
        if bar > 1:
            site._updateProperty( 'bar', ('Bar',) )
            site.moo = ['Moo']

        return site

    def setUp(self):
        import Products.CMFCore.exportimport

        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportSitePropertiesTests(_SitePropertiesSetup):

    def test_empty(self):
        from Products.CMFCore.exportimport.properties \
                import exportSiteProperties

        site = self._initSite(0, 0)
        context = DummyExportContext(site)
        exportSiteProperties(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'properties.xml')
        self._compareDOM(text, _EMPTY_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal(self):
        from Products.CMFCore.exportimport.properties \
                import exportSiteProperties

        site = self._initSite()
        context = DummyExportContext( site )
        exportSiteProperties(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'properties.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importSitePropertiesTests(_SitePropertiesSetup):

    def test_empty_default_purge(self):
        from Products.CMFCore.exportimport.properties \
                import importSiteProperties

        site = self._initSite()

        self.assertEqual( len( site.propertyIds() ), 4 )
        self.failUnless( 'foo' in site.propertyIds() )
        self.assertEqual( site.getProperty('foo'), 'Foo' )
        self.failUnless( 'bar' in site.propertyIds() )
        self.assertEqual( site.getProperty('bar'), ('Bar',) )

        context = DummyImportContext(site)
        context._files['properties.xml'] = _EMPTY_EXPORT
        importSiteProperties(context)

        self.assertEqual( len( site.propertyIds() ), 1 )

    def test_empty_explicit_purge(self):
        from Products.CMFCore.exportimport.properties \
                import importSiteProperties

        site = self._initSite()

        self.assertEqual( len( site.propertyIds() ), 4 )
        self.failUnless( 'foo' in site.propertyIds() )
        self.assertEqual( site.getProperty('foo'), 'Foo' )
        self.failUnless( 'bar' in site.propertyIds() )
        self.assertEqual( site.getProperty('bar'), ('Bar',) )

        context = DummyImportContext(site, True)
        context._files['properties.xml'] = _EMPTY_EXPORT
        importSiteProperties(context)

        self.assertEqual( len( site.propertyIds() ), 1 )

    def test_empty_skip_purge(self):
        from Products.CMFCore.exportimport.properties \
                import importSiteProperties

        site = self._initSite()

        self.assertEqual( len( site.propertyIds() ), 4 )
        self.failUnless( 'foo' in site.propertyIds() )
        self.assertEqual( site.getProperty('foo'), 'Foo' )
        self.failUnless( 'bar' in site.propertyIds() )
        self.assertEqual( site.getProperty('bar'), ('Bar',) )

        context = DummyImportContext(site, False)
        context._files['properties.xml'] = _EMPTY_EXPORT
        importSiteProperties(context)

        self.assertEqual( len( site.propertyIds() ), 4 )
        self.failUnless( 'foo' in site.propertyIds() )
        self.assertEqual( site.getProperty('foo'), 'Foo' )
        self.failUnless( 'bar' in site.propertyIds() )
        self.assertEqual( site.getProperty('bar'), ('Bar',) )

    def test_normal(self):
        from Products.CMFCore.exportimport.properties \
                import importSiteProperties

        site = self._initSite(0,0)

        self.assertEqual( len( site.propertyIds() ), 1 )

        context = DummyImportContext(site)
        context._files['properties.xml'] = _NORMAL_EXPORT
        importSiteProperties(context)

        self.assertEqual( len( site.propertyIds() ), 4 )
        self.failUnless( 'foo' in site.propertyIds() )
        self.assertEqual( site.getProperty('foo'), 'Foo' )
        self.failUnless( 'bar' in site.propertyIds() )
        self.assertEqual( site.getProperty('bar'), ('Bar',) )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(PropertiesXMLAdapterTests),
        unittest.makeSuite(exportSitePropertiesTests),
        unittest.makeSuite(importSitePropertiesTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
