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
"""Types tool xml adapter and setup handler unit tests.

$Id: test_typeinfo.py 39983 2005-11-08 18:45:42Z yuppie $
"""

import unittest
import Testing

import Products
from OFS.Folder import Folder
from Products.Five import zcml

from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import AccessContentsInformation
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.tests.base.testcase import PlacelessSetup
from Products.CMFCore.TypesTool import FactoryTypeInformation
from Products.CMFCore.TypesTool import ScriptableTypeInformation
from Products.CMFCore.TypesTool import TypesTool

_FTI_BODY = """\
<?xml version="1.0"?>
<object name="foo_fti" meta_type="Factory-based Type Information"
   xmlns:i18n="http://xml.zope.org/namespaces/i18n">
 <property name="title"></property>
 <property name="description"></property>
 <property name="content_icon"></property>
 <property name="content_meta_type"></property>
 <property name="product"></property>
 <property name="factory"></property>
 <property name="immediate_view"></property>
 <property name="global_allow">True</property>
 <property name="filter_content_types">True</property>
 <property name="allowed_content_types"/>
 <property name="allow_discussion">False</property>
 <alias from="(Default)" to="foo"/>
 <alias from="view" to="foo"/>
 <action title="Foo" action_id="foo_action" category="Bar"
    condition_expr="python:1" url_expr="string:${object_url}/foo"
    visible="True"/>
</object>
"""

_TYPESTOOL_BODY = """\
<?xml version="1.0"?>
<object name="portal_types" meta_type="CMF Types Tool">
 <property name="title"></property>
 <object name="foo_type" meta_type="Factory-based Type Information"/>
</object>
"""

_TI_LIST = ({
    'id':                    'foo',
    'title':                 'Foo',
    'description':           'Foo things',
    'i18n_domain':           'foo_domain',
    'content_meta_type':     'Foo Thing',
    'content_icon':          'foo.png',
    'product':               'CMFSetup',
    'factory':               'addFoo',
    'immediate_view':        'foo_view',
    'filter_content_types':  False,
    'allowed_content_types': (),
    'allow_discussion':      False,
    'global_allow':          False,
    'aliases': {'(Default)': 'foo_view',
                'view':      'foo_view',
                },
    'actions': ({'id':     'view',
                 'name':   'View',
                 'action': 'string:${object_url}/foo_view',
                 'permissions': (View,),
                 },
                {'id':     'edit',
                 'name':   'Edit',
                 'action': 'string:${object_url}/foo_edit_form',
                 'permissions': (ModifyPortalContent,),
                 },
                {'id':     'metadata',
                 'name':   'Metadata',
                 'action': 'string:${object_url}/metadata_edit_form',
                 'permissions': (ModifyPortalContent,),
                 },
                ),
    }, {
    'id':                    'bar',
    'title':                 'Bar',
    'description':           'Bar things',
    'content_meta_type':     'Bar Thing',
    'content_icon':          'bar.png',
    'constructor_path':      'make_bar',
    'permission':            'Add portal content',
    'immediate_view':        'bar_view',
    'filter_content_types':  True,
    'allowed_content_types': ('foo',),
    'allow_discussion':      True,
    'global_allow':          True,
    'aliases': {'(Default)': 'bar_view',
                'view':      'bar_view',
                },
    'actions': ({'id':     'view',
                 'name':   'View',
                 'action': 'string:${object_url}/bar_view',
                 'permissions': (View,),
                 },
                {'id':     'edit',
                 'name':   'Edit',
                 'action': 'string:${object_url}/bar_edit_form',
                 'permissions': (ModifyPortalContent,),
                 },
                {'id':     'contents',
                 'name':   'Contents',
                 'action': 'string:${object_url}/folder_contents',
                 'permissions': (AccessContentsInformation,),
                 },
                {'id':     'metadata',
                 'name':   'Metadata',
                 'action': 'string:${object_url}/metadata_edit_form',
                 'permissions': (ModifyPortalContent,),
                 },
               ),
    })

_TI_LIST_WITH_FILENAME = []

for original in _TI_LIST:
    duplicate = original.copy()
    duplicate['id'] = '%s object' % original['id']
    _TI_LIST_WITH_FILENAME.append(duplicate)

_EMPTY_TOOL_EXPORT = """\
<?xml version="1.0"?>
<object name="portal_types" meta_type="CMF Types Tool">
 <property name="title"/>
</object>
"""

_EMPTY_TOOL_EXPORT_V1 = """\
<?xml version="1.0"?>
<types-tool>
</types-tool>
"""

_NORMAL_TOOL_EXPORT = """\
<?xml version="1.0"?>
<object name="portal_types" meta_type="CMF Types Tool">
 <property name="title"/>
 <object name="bar" meta_type="Scriptable Type Information"/>
 <object name="foo" meta_type="Factory-based Type Information"/>
</object>
"""

_NORMAL_TOOL_EXPORT_V1 = """\
<?xml version="1.0"?>
<types-tool>
 <type id="bar" />
 <type id="foo" />
</types-tool>
"""

_FILENAME_EXPORT = """\
<?xml version="1.0"?>
<object name="portal_types" meta_type="CMF Types Tool">
 <property name="title"/>
 <object name="bar object" meta_type="Scriptable Type Information"/>
 <object name="foo object" meta_type="Factory-based Type Information"/>
</object>
"""

_FILENAME_EXPORT_V1 = """\
<?xml version="1.0"?>
<types-tool>
 <type id="bar object" filename="types/bar_object.xml" />
 <type id="foo object" filename="types/foo_object.xml" />
</types-tool>
"""

_UPDATE_TOOL_IMPORT = """\
<?xml version="1.0"?>
<types-tool>
 <type id="foo"/>
</types-tool>
"""

_FOO_OLD_EXPORT = """\
<?xml version="1.0"?>
<type-info
   id="%s"
   kind="Factory-based Type Information"
   title="Foo"
   meta_type="Foo Thing"
   icon="foo.png"
   product="CMFSetup"
   factory="addFoo"
   immediate_view="foo_view"
   filter_content_types="False"
   allow_discussion="False"
   global_allow="False" >
  <description>Foo things</description>
  <aliases>
   <alias from="(Default)" to="foo_view" />
   <alias from="view" to="foo_view" />
  </aliases>
  <action
     action_id="view"
     title="View"
     url_expr="string:${object_url}/foo_view"
     condition_expr=""
     category="object"
     visible="True">
   <permission>View</permission>
  </action>
  <action
     action_id="edit"
     title="Edit"
     url_expr="string:${object_url}/foo_edit_form"
     condition_expr=""
     category="object"
     visible="True">
   <permission>Modify portal content</permission>
  </action>
  <action
     action_id="metadata"
     title="Metadata"
     url_expr="string:${object_url}/metadata_edit_form"
     condition_expr=""
     category="object"
     visible="True">
   <permission>Modify portal content</permission>
  </action>
</type-info>
"""

_FOO_EXPORT = """\
<?xml version="1.0"?>
<object name="%s" meta_type="Factory-based Type Information"
   xmlns:i18n="http://xml.zope.org/namespaces/i18n">
 <property name="title">Foo</property>
 <property name="description">Foo things</property>
 <property name="content_icon">foo.png</property>
 <property name="content_meta_type">Foo Thing</property>
 <property name="product">CMFSetup</property>
 <property name="factory">addFoo</property>
 <property name="immediate_view">foo_view</property>
 <property name="global_allow">False</property>
 <property name="filter_content_types">False</property>
 <property name="allowed_content_types"/>
 <property name="allow_discussion">False</property>
 <alias from="(Default)" to="foo_view"/>
 <alias from="view" to="foo_view"/>
 <action title="View" action_id="view" category="object" condition_expr=""
    url_expr="string:${object_url}/foo_view" visible="True">
  <permission value="View"/>
 </action>
 <action title="Edit" action_id="edit" category="object" condition_expr=""
    url_expr="string:${object_url}/foo_edit_form" visible="True">
  <permission value="Modify portal content"/>
 </action>
 <action title="Metadata" action_id="metadata" category="object"
    condition_expr="" url_expr="string:${object_url}/metadata_edit_form"
    visible="True">
  <permission value="Modify portal content"/>
 </action>
</object>
"""

_BAR_OLD_EXPORT = """\
<?xml version="1.0"?>
<type-info
   id="%s"
   kind="Scriptable Type Information"
   title="Bar"
   meta_type="Bar Thing"
   icon="bar.png"
   constructor_path="make_bar"
   permission="Add portal content"
   immediate_view="bar_view"
   filter_content_types="True"
   allow_discussion="True"
   global_allow="True" >
  <description>Bar things</description>
  <allowed_content_type>foo</allowed_content_type>
  <aliases>
   <alias from="(Default)" to="bar_view" />
   <alias from="view" to="bar_view" />
  </aliases>
  <action
     action_id="view"
     title="View"
     url_expr="string:${object_url}/bar_view"
     condition_expr=""
     category="object"
     visible="True">
   <permission>View</permission>
  </action>
  <action
     action_id="edit"
     title="Edit"
     url_expr="string:${object_url}/bar_edit_form"
     condition_expr=""
     category="object"
     visible="True">
   <permission>Modify portal content</permission>
  </action>
  <action
     action_id="contents"
     title="Contents"
     url_expr="string:${object_url}/folder_contents"
     condition_expr=""
     category="object"
     visible="True">
   <permission>Access contents information</permission>
  </action>
  <action
     action_id="metadata"
     title="Metadata"
     url_expr="string:${object_url}/metadata_edit_form"
     condition_expr=""
     category="object"
     visible="True">
   <permission>Modify portal content</permission>
  </action>
</type-info>
"""

_BAR_EXPORT = """\
<?xml version="1.0"?>
<object name="%s" meta_type="Scriptable Type Information"
   xmlns:i18n="http://xml.zope.org/namespaces/i18n">
 <property name="title">Bar</property>
 <property name="description">Bar things</property>
 <property name="content_icon">bar.png</property>
 <property name="content_meta_type">Bar Thing</property>
 <property name="permission">Add portal content</property>
 <property name="constructor_path">make_bar</property>
 <property name="immediate_view">bar_view</property>
 <property name="global_allow">True</property>
 <property name="filter_content_types">True</property>
 <property name="allowed_content_types">
  <element value="foo"/>
 </property>
 <property name="allow_discussion">True</property>
 <alias from="(Default)" to="bar_view"/>
 <alias from="view" to="bar_view"/>
 <action title="View" action_id="view" category="object" condition_expr=""
    url_expr="string:${object_url}/bar_view" visible="True">
  <permission value="View"/>
 </action>
 <action title="Edit" action_id="edit" category="object" condition_expr=""
    url_expr="string:${object_url}/bar_edit_form" visible="True">
  <permission value="Modify portal content"/>
 </action>
 <action title="Contents" action_id="contents" category="object"
    condition_expr="" url_expr="string:${object_url}/folder_contents"
    visible="True">
  <permission value="Access contents information"/>
 </action>
 <action title="Metadata" action_id="metadata" category="object"
    condition_expr="" url_expr="string:${object_url}/metadata_edit_form"
    visible="True">
  <permission value="Modify portal content"/>
 </action>
</object>
"""

_UPDATE_FOO_IMPORT = """\
<object name="foo">
 <alias from="spam" to="eggs"/>
</object>
"""


class TypeInformationXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.typeinfo \
                import TypeInformationXMLAdapter

        return TypeInformationXMLAdapter

    def _populate(self, obj):
        obj.addAction('foo_action', 'Foo', 'string:${object_url}/foo',
                      'python:1', (), 'Bar')

    def _verifyImport(self, obj):
        self.assertEqual(type(obj._aliases), dict)
        self.assertEqual(obj._aliases, {'(Default)': 'foo', 'view': 'foo'})
        self.assertEqual(type(obj._aliases['view']), str)
        self.assertEqual(obj._aliases['view'], 'foo')
        self.assertEqual(type(obj._actions), tuple)
        self.assertEqual(type(obj._actions[0].id), str)
        self.assertEqual(obj._actions[0].id, 'foo_action')
        self.assertEqual(type(obj._actions[0].title), str)
        self.assertEqual(obj._actions[0].title, 'Foo')
        self.assertEqual(type(obj._actions[0].description), str)
        self.assertEqual(obj._actions[0].description, '')
        self.assertEqual(type(obj._actions[0].category), str)
        self.assertEqual(obj._actions[0].category, 'Bar')
        self.assertEqual(type(obj._actions[0].condition.text), str)
        self.assertEqual(obj._actions[0].condition.text, 'python:1')

    def setUp(self):
        import Products.CMFCore
        from Products.CMFCore.TypesTool import FactoryTypeInformation

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore)

        self._obj = FactoryTypeInformation('foo_fti')
        self._BODY = _FTI_BODY


class TypesToolXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.typeinfo \
                import TypesToolXMLAdapter

        return TypesToolXMLAdapter

    def _populate(self, obj):
        from Products.CMFCore.TypesTool import FactoryTypeInformation

        obj._setObject('foo_type', FactoryTypeInformation('foo_type'))

    def setUp(self):
        import Products.CMFCore
        from Products.CMFCore.TypesTool import TypesTool

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore)

        self._obj = TypesTool()
        self._BODY = _TYPESTOOL_BODY


class _TypeInfoSetup(PlacelessSetup, BaseRegistryTests):

    def _initSite(self, foo=0):
        self.root.site = Folder(id='site')
        site = self.root.site
        ttool = site.portal_types = TypesTool()

        if foo == 1:
            fti = _TI_LIST[0].copy()
            ttool._setObject(fti['id'], FactoryTypeInformation(**fti))
            sti = _TI_LIST[1].copy()
            ttool._setObject(sti['id'], ScriptableTypeInformation(**sti))
        elif foo == 2:
            fti = _TI_LIST_WITH_FILENAME[0].copy()
            ttool._setObject(fti['id'], FactoryTypeInformation(**fti))
            sti = _TI_LIST_WITH_FILENAME[1].copy()
            ttool._setObject(sti['id'], ScriptableTypeInformation(**sti))

        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('permissions.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportTypesToolTests(_TypeInfoSetup):

    def test_empty(self):
        from Products.CMFCore.exportimport.typeinfo import exportTypesTool

        site = self._initSite()
        context = DummyExportContext(site)
        exportTypesTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'types.xml')
        self._compareDOM(text, _EMPTY_TOOL_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal(self):
        from Products.CMFCore.exportimport.typeinfo import exportTypesTool

        site = self._initSite(1)
        context = DummyExportContext(site)
        exportTypesTool(context)

        self.assertEqual(len(context._wrote), 3)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'types.xml')
        self._compareDOM(text, _NORMAL_TOOL_EXPORT)
        self.assertEqual(content_type, 'text/xml')

        filename, text, content_type = context._wrote[2]
        self.assertEqual(filename, 'types/bar.xml')
        self._compareDOM(text, _BAR_EXPORT % 'bar')
        self.assertEqual(content_type, 'text/xml')

        filename, text, content_type = context._wrote[1]
        self.assertEqual(filename, 'types/foo.xml')
        self._compareDOM(text, _FOO_EXPORT % 'foo')
        self.assertEqual(content_type, 'text/xml')

    def test_with_filenames(self):
        from Products.CMFCore.exportimport.typeinfo import exportTypesTool

        site = self._initSite(2)
        context = DummyExportContext(site)
        exportTypesTool(context)

        self.assertEqual(len(context._wrote), 3)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'types.xml')
        self._compareDOM(text, _FILENAME_EXPORT)
        self.assertEqual(content_type, 'text/xml')
        filename, text, content_type = context._wrote[2]
        self.assertEqual(filename, 'types/bar_object.xml')
        self._compareDOM(text, _BAR_EXPORT % 'bar object')
        self.assertEqual(content_type, 'text/xml')
        filename, text, content_type = context._wrote[1]
        self.assertEqual(filename, 'types/foo_object.xml')
        self._compareDOM(text, _FOO_EXPORT % 'foo object')
        self.assertEqual(content_type, 'text/xml')


class importTypesToolTests(_TypeInfoSetup):

    _EMPTY_TOOL_EXPORT = _EMPTY_TOOL_EXPORT
    _FILENAME_EXPORT = _FILENAME_EXPORT
    _NORMAL_TOOL_EXPORT = _NORMAL_TOOL_EXPORT

    def test_empty_default_purge(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite(1)
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 2)

        context = DummyImportContext(site)
        context._files['types.xml'] = self._EMPTY_TOOL_EXPORT
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 0)

    def test_empty_explicit_purge(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite(1)
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 2)

        context = DummyImportContext(site, True)
        context._files['types.xml'] = self._EMPTY_TOOL_EXPORT
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 0)

    def test_empty_skip_purge(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite(1)
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 2)

        context = DummyImportContext(site, False)
        context._files['types.xml'] = self._EMPTY_TOOL_EXPORT
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 2)

    def test_normal(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite()
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 0)

        context = DummyImportContext(site)
        context._files['types.xml'] = self._NORMAL_TOOL_EXPORT
        context._files['types/foo.xml'] = _FOO_EXPORT % 'foo'
        context._files['types/bar.xml'] = _BAR_EXPORT % 'bar'
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 2)
        self.failUnless('foo' in tool.objectIds())
        self.failUnless('bar' in tool.objectIds())

    def test_old_xml(self):
        from Products.CMFCore.exportimport.typeinfo import exportTypesTool
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite()
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 0)

        context = DummyImportContext(site)
        context._files['types.xml'] = self._NORMAL_TOOL_EXPORT
        context._files['types/foo.xml'] = _FOO_OLD_EXPORT % 'foo'
        context._files['types/bar.xml'] = _BAR_OLD_EXPORT % 'bar'
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 2)
        self.failUnless('foo' in tool.objectIds())
        self.failUnless('bar' in tool.objectIds())

        context = DummyExportContext(site)
        exportTypesTool(context)

        filename, text, content_type = context._wrote[1]
        self.assertEqual(filename, 'types/bar.xml')
        self._compareDOM(text, _BAR_EXPORT % 'bar')
        self.assertEqual(content_type, 'text/xml')

    def test_with_filenames(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite()
        tool = site.portal_types

        self.assertEqual(len(tool.objectIds()), 0)

        context = DummyImportContext(site)
        context._files['types.xml'] = self._FILENAME_EXPORT
        context._files['types/foo_object.xml'] = _FOO_EXPORT % 'foo object'
        context._files['types/bar_object.xml'] = _BAR_EXPORT % 'bar object'
        importTypesTool(context)

        self.assertEqual(len(tool.objectIds()), 2)
        self.failUnless('foo object' in tool.objectIds())
        self.failUnless('bar object' in tool.objectIds())

    def test_normal_update(self):
        from Products.CMFCore.exportimport.typeinfo import importTypesTool

        site = self._initSite()
        tool = site.portal_types

        context = DummyImportContext(site)
        context._files['types.xml'] = self._NORMAL_TOOL_EXPORT
        context._files['types/foo.xml'] = _FOO_EXPORT % 'foo'
        context._files['types/bar.xml'] = _BAR_EXPORT % 'bar'
        importTypesTool(context)

        self.assertEqual(tool.foo.title, 'Foo')
        self.assertEqual(tool.foo.content_meta_type, 'Foo Thing')
        self.assertEqual(tool.foo.content_icon, 'foo.png')
        self.assertEqual(tool.foo.immediate_view, 'foo_view')
        self.assertEqual(tool.foo._aliases,
                         {'(Default)': 'foo_view', 'view': 'foo_view'})

        context = DummyImportContext(site, False)
        context._files['types.xml'] = _UPDATE_TOOL_IMPORT
        context._files['types/foo.xml'] = _UPDATE_FOO_IMPORT
        importTypesTool(context)

        self.assertEqual(tool.foo.title, 'Foo')
        self.assertEqual(tool.foo.content_meta_type, 'Foo Thing')
        self.assertEqual(tool.foo.content_icon, 'foo.png')
        self.assertEqual(tool.foo.immediate_view, 'foo_view')
        self.assertEqual(tool.foo._aliases,
               {'(Default)': 'foo_view', 'view': 'foo_view', 'spam': 'eggs'})

class importTypesToolV1Tests(importTypesToolTests):

    _EMPTY_TOOL_EXPORT = _EMPTY_TOOL_EXPORT_V1
    _FILENAME_EXPORT = _FILENAME_EXPORT_V1
    _NORMAL_TOOL_EXPORT = _NORMAL_TOOL_EXPORT_V1


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(TypeInformationXMLAdapterTests),
        unittest.makeSuite(TypesToolXMLAdapterTests),
        unittest.makeSuite(exportTypesToolTests),
        unittest.makeSuite(importTypesToolTests),
        unittest.makeSuite(importTypesToolV1Tests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
