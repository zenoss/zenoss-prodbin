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
"""Actions tool node adapter unit tests.

$Id: test_actions.py 39983 2005-11-08 18:45:42Z yuppie $
"""

import unittest
import Testing
import Zope2
Zope2.startup()

import Products
from Acquisition import Implicit
from Acquisition import aq_parent
from OFS.Folder import Folder
from OFS.OrderedFolder import OrderedFolder
from Products.Five import zcml
from zope.interface import implements

from Products.CMFCore.ActionProviderBase import ActionProviderBase
from Products.CMFCore.interfaces import IActionsTool
from Products.CMFCore.interfaces.portal_actions \
    import ActionProvider as IActionProvider
from Products.CMFCore.tests.base.dummy import DummySite
from Products.CMFCore.tests.base.testcase import PlacelessSetup
from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.testing import NodeAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

_ACTIONSTOOL_BODY = """\
<?xml version="1.0"?>
<object name="portal_actions" meta_type="CMF Actions Tool">
 <action-provider name="portal_actions"/>
</object>
"""

_EMPTY_EXPORT = """\
<?xml version="1.0"?>
<object meta_type="CMF Actions Tool" name="portal_actions">
 <action-provider name="portal_actions"/>
</object>
"""

_NORMAL_EXPORT = """\
<?xml version="1.0"?>
<object meta_type="CMF Actions Tool" name="portal_actions">
 <action-provider name="portal_actions"/>
 <action-provider name="portal_foo">
  <action action_id="foo"
          title="Foo"
          url_expr="string:${object_url}/foo"
          condition_expr="python:1"
          category="dummy"
          visible="True"/>
 </action-provider>
 <action-provider name="portal_bar">
  <action action_id="bar"
          title="Bar"
          url_expr="string:${object_url}/bar"
          condition_expr="python:0"
          category="dummy"
          visible="False">
   <permission>Manage portal</permission>
  </action>
 </action-provider>
</object>
"""

_REMOVE_IMPORT = """\
<?xml version="1.0"?>
<actions-tool>
 <action-provider id="portal_actions" remove="">
 </action-provider>
 <action-provider id="not_existing" remove="">
 </action-provider>
 <action-provider id="portal_bar" remove="">
 </action-provider>
</actions-tool>
"""


class DummyTool(OrderedFolder, ActionProviderBase):

    __implements__ = IActionProvider


class DummyUser(Implicit):

    def getId(self):
        return 'dummy'


class DummyMembershipTool(DummyTool):

    def isAnonymousUser(self):
        return False

    def getAuthenticatedMember(self):
        return DummyUser().__of__(aq_parent(self))


class DummyActionsTool(DummyTool):

    implements(IActionsTool)
    id = 'portal_actions'
    meta_type = 'CMF Actions Tool'

    def __init__(self):
        self._providers = []

    def addActionProvider(self, provider_name):
        self._providers.append(provider_name)

    def listActionProviders(self):
        return self._providers[:]

    def deleteActionProvider(self, provider_name):
        self._providers = [ x for x in self._providers if x != provider_name ]


class ActionsToolXMLAdapterTests(BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.actions \
                import ActionsToolXMLAdapter

        return ActionsToolXMLAdapter

    def _populate(self, obj):
        obj.action_providers = ('portal_actions',)
        obj._actions = ()

    def _verifyImport(self, obj):
        self.assertEqual(type(obj.action_providers), tuple)
        self.assertEqual(obj.action_providers, ('portal_actions',))
        self.assertEqual(type(obj.action_providers[0]), str)
        self.assertEqual(obj.action_providers[0], 'portal_actions')

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.ActionsTool import ActionsTool

        BodyAdapterTestCase.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        site = DummySite('site')
        site._setObject('portal_actions', ActionsTool('portal_actions'))
        self._obj = site.portal_actions
        self._BODY = _ACTIONSTOOL_BODY


class _ActionSetup(PlacelessSetup, BaseRegistryTests):

    def _initSite(self, foo=2, bar=2):
        self.root.site = Folder(id='site')
        site = self.root.site
        site.portal_membership = DummyMembershipTool()

        site.portal_actions = DummyActionsTool()
        site.portal_actions.addActionProvider('portal_actions')

        if foo > 0:
            site.portal_foo = DummyTool()

        if foo > 1:
            site.portal_foo.addAction(id='foo',
                                      name='Foo',
                                      action='foo',
                                      condition='python:1',
                                      permission=(),
                                      category='dummy',
                                      visible=1)
            site.portal_actions.addActionProvider('portal_foo')

        if bar > 0:
            site.portal_bar = DummyTool()

        if bar > 1:
            site.portal_bar.addAction(id='bar',
                                      name='Bar',
                                      action='bar',
                                      condition='python:0',
                                      permission=('Manage portal',),
                                      category='dummy',
                                      visible=0)
            site.portal_actions.addActionProvider('portal_bar')

        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

    def tearDown(self):
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportActionProvidersTests(_ActionSetup):

    def test_unchanged(self):
        from Products.CMFCore.exportimport.actions \
                import exportActionProviders

        site = self._initSite(0, 0)
        context = DummyExportContext(site)
        exportActionProviders(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'actions.xml')
        self._compareDOM(text, _EMPTY_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal(self):
        from Products.CMFCore.exportimport.actions \
                import exportActionProviders

        site = self._initSite()
        context = DummyExportContext(site)
        exportActionProviders(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'actions.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importActionProvidersTests(_ActionSetup):

    def test_empty_default_purge(self):
        from Products.CMFCore.exportimport.actions \
                import importActionProviders

        site = self._initSite(2, 0)
        atool = site.portal_actions

        self.assertEqual(len(atool.listActionProviders()), 2)
        self.failUnless('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())

        context = DummyImportContext(site)
        context._files['actions.xml'] = _EMPTY_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 1)
        self.failIf('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())
        self.assertEqual(len(atool.objectIds()), 0)

    def test_empty_explicit_purge(self):
        from Products.CMFCore.exportimport.actions \
                import importActionProviders

        site = self._initSite(2, 0)
        atool = site.portal_actions

        self.assertEqual(len(atool.listActionProviders()), 2)
        self.failUnless('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())

        context = DummyImportContext(site, True)
        context._files['actions.xml'] = _EMPTY_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 1)
        self.failIf('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())
        self.assertEqual(len(atool.objectIds()), 0)

    def test_empty_skip_purge(self):
        from Products.CMFCore.exportimport.actions \
                import importActionProviders

        site = self._initSite(2, 0)
        atool = site.portal_actions

        self.assertEqual(len(atool.listActionProviders()), 2)
        self.failUnless('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())

        context = DummyImportContext(site, False)
        context._files['actions.xml'] = _EMPTY_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 2)
        self.failUnless('portal_foo' in atool.listActionProviders())
        self.failUnless('portal_actions' in atool.listActionProviders())

    def test_normal(self):
        from Products.CMFCore.exportimport.actions \
                import exportActionProviders
        from Products.CMFCore.exportimport.actions \
                import importActionProviders

        site = self._initSite(1, 1)
        atool = site.portal_actions
        foo = site.portal_foo
        bar = site.portal_bar

        self.assertEqual(len(atool.listActionProviders()), 1)
        self.failIf('portal_foo' in atool.listActionProviders())
        self.failIf(foo.listActions())
        self.failIf('portal_bar' in atool.listActionProviders())
        self.failIf(bar.listActions())
        self.failUnless('portal_actions' in atool.listActionProviders())

        context = DummyImportContext(site)
        context._files['actions.xml'] = _NORMAL_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 3)
        self.failUnless('portal_actions' in atool.listActionProviders())
        self.failUnless('portal_foo' in atool.listActionProviders())
        self.failUnless(foo.listActions())
        self.failUnless('portal_bar' in atool.listActionProviders())
        self.failUnless(bar.listActions())

        # complete the roundtrip
        context = DummyExportContext(site)
        exportActionProviders(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'actions.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_import_extension(self):
        from Products.CMFCore.exportimport.actions import importActionProviders

        site = self._initSite(2, 2)
        atool = site.portal_actions
        foo = site.portal_foo
        bar = site.portal_bar

        # Normal import.
        context = DummyImportContext(site)
        context._files['actions.xml'] = _NORMAL_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 3)
        self.assertEqual([a.id for a in foo.listActions()], ['foo'])
        self.assertEqual([a.id for a in bar.listActions()], ['bar'])

        # Add an action manually to bar, it shouldn't get
        # removed by the next non-purge import.
        bar.addAction(id='gee',
                      name='Gee',
                      action='geeman',
                      condition='python:maybe()',
                      permission=('Manage portal',),
                      category='dummy',
                      visible=0)
        # Modify actions.
        foo.listActions()[0].title = 'OtherFoo'
        bar.listActions()[0].title = 'OtherBar'

        self.assertEqual([a.id for a in bar.listActions()], ['bar', 'gee'])

        # Now reimport as extension profile, without purge.
        context = DummyImportContext(site, False)
        context._files['actions.xml'] = _NORMAL_EXPORT
        importActionProviders(context)

        self.assertEqual(len(atool.listActionProviders()), 3)
        self.assertEqual([a.id for a in foo.listActions()], ['foo'])
        self.assertEqual(foo.listActions()[0].title, 'Foo')
        self.assertEqual([a.id for a in bar.listActions()], ['gee', 'bar'])
        self.assertEqual([a.title for a in bar.listActions()], ['Gee', 'Bar'])

    def test_remove_skip_purge(self):
        from Products.CMFCore.exportimport.actions \
                import importActionProviders

        site = self._initSite(2, 2)
        atool = site.portal_actions

        self.assertEqual(atool.listActionProviders(),
                          ['portal_actions', 'portal_foo', 'portal_bar'])

        context = DummyImportContext(site, False)
        context._files['actions.xml'] = _REMOVE_IMPORT
        importActionProviders(context)

        self.assertEqual(atool.listActionProviders(), ['portal_foo'])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(ActionsToolXMLAdapterTests),
        unittest.makeSuite(exportActionProvidersTests),
        unittest.makeSuite(importActionProvidersTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
