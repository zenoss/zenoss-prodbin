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
"""Skins tool xml adapter and setup handler unit tests.

$Id: test_skins.py 40879 2005-12-18 22:08:21Z yuppie $
"""

import unittest
import Testing
import Zope2
Zope2.startup()

import os

import Products
from OFS.Folder import Folder
from Products.Five import zcml
from zope.interface import implements

from Products.GenericSetup.testing import BodyAdapterTestCase
from Products.GenericSetup.testing import NodeAdapterTestCase
from Products.GenericSetup.tests.common import BaseRegistryTests
from Products.GenericSetup.tests.common import DOMComparator
from Products.GenericSetup.tests.common import DummyExportContext
from Products.GenericSetup.tests.common import DummyImportContext

from Products.CMFCore.interfaces import ISkinsTool
from Products.CMFCore.tests.base.testcase import PlacelessSetup

_TESTS_PATH = os.path.split(__file__)[0]

_DIRECTORYVIEW_XML = """\
<object name="foo_directoryview" meta_type="Filesystem Directory View"
   directory="CMFCore/exportimport/tests/one"/>
"""

_SKINSTOOL_BODY = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="CMF Skins Tool" allow_any="False"
   cookie_persistence="False" default_skin="" request_varname="portal_skin">
 <object name="foo_directoryview" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/one"/>
 <skin-path name="foo_path">
  <layer name="one"/>
 </skin-path>
</object>
"""

_EMPTY_EXPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool" allow_any="False"
   cookie_persistence="False" default_skin="default_skin"
   request_varname="request_varname"/>
"""

_NORMAL_EXPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool" allow_any="True"
   cookie_persistence="True" default_skin="basic" request_varname="skin_var">
 <object name="one" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/one"/>
 <object name="three" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/three"/>
 <object name="two" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/two"/>
 <skin-path name="basic">
  <layer name="one"/>
 </skin-path>
 <skin-path name="fancy">
  <layer name="three"/>
  <layer name="two"/>
  <layer name="one"/>
 </skin-path>
</object>
"""

_FRAGMENT1_IMPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool">
 <object name="three" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/three"/>
 <skin-path name="*">
  <layer name="three" insert-before="two"/>
 </skin-path>
</object>
"""

_FRAGMENT2_IMPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool">
 <object name="four" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/four"/>
 <skin-path name="*">
  <layer name="four" insert-after="three"/>
 </skin-path>
</object>
"""

_FRAGMENT3_IMPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool">
 <object name="three" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/three"/>
 <object name="four" meta_type="Filesystem Directory View"
    directory="CMFCore/exportimport/tests/four"/>
 <skin-path name="*">
  <layer name="three" insert-before="*"/>
  <layer name="four" insert-after="*"/>
 </skin-path>
</object>
"""

_FRAGMENT4_IMPORT = """\
<?xml version="1.0"?>
<object name="portal_skins" meta_type="Dummy Skins Tool">
 <skin-path name="*">
  <layer name="three" remove="1"/>
 </skin-path>
</object>
"""

_EMPTY_EXPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool default_skin="default_skin"
            request_varname="request_varname"
            allow_any="False"
            cookie_persistence="False">
</skins-tool>
"""

_NORMAL_EXPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool default_skin="basic"
            request_varname="skin_var"
            allow_any="True"
            cookie_persistence="True">
 <skin-directory id="one" directory="CMFCore/exportimport/tests/one" />
 <skin-directory id="three" directory="CMFCore/exportimport/tests/three" />
 <skin-directory id="two" directory="CMFCore/exportimport/tests/two" />
 <skin-path id="basic">
  <layer name="one" />
 </skin-path>
 <skin-path id="fancy">
  <layer name="three" />
  <layer name="two" />
  <layer name="one" />
 </skin-path>
</skins-tool>
"""

_FRAGMENT1_IMPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool>
 <skin-directory id="three" directory="CMFCore/exportimport/tests/three" />
 <skin-path id="*">
  <layer name="three" insert-before="two"/>
 </skin-path>
</skins-tool>
"""

_FRAGMENT2_IMPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool>
 <skin-directory id="four" directory="CMFCore/exportimport/tests/four" />
 <skin-path id="*">
  <layer name="four" insert-after="three"/>
 </skin-path>
</skins-tool>
"""

_FRAGMENT3_IMPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool>
 <skin-directory id="three" directory="CMFCore/exportimport/tests/three" />
 <skin-directory id="four" directory="CMFCore/exportimport/tests/four" />
 <skin-path id="*">
  <layer name="three" insert-before="*"/>
  <layer name="four" insert-after="*"/>
 </skin-path>
</skins-tool>
"""

_FRAGMENT4_IMPORT_V1 = """\
<?xml version="1.0"?>
<skins-tool>
 <skin-path id="*">
  <layer name="three" remove="1"/>
 </skin-path>
</skins-tool>
"""


class DummySite(Folder):

    _skin_setup_called = False

    def clearCurrentSkin(self):
        pass

    def setupCurrentSkin(self, REQUEST):
        self._skin_setup_called = True


class DummySkinsTool(Folder):

    implements(ISkinsTool)

    meta_type = 'Dummy Skins Tool'
    default_skin = 'default_skin'
    request_varname = 'request_varname'
    allow_any = False
    cookie_persistence = False

    def __init__(self, selections=None, fsdvs=()):
        self._selections = selections or {}

        for id, obj in fsdvs:
            self._setObject(id, obj)

    def _getSelections(self):
        return self._selections

    def getId(self):
        return 'portal_skins'

    def getSkinPaths(self):
        result = list(self._selections.items())
        result.sort()
        return result

    def addSkinSelection(self, skinname, skinpath, test=0, make_default=0):
        self._selections[skinname] = skinpath


class _DVRegistrySetup:
    
    def setUp(self):
        from Products.CMFCore import DirectoryView

        self._olddirreg = DirectoryView._dirreg
        DirectoryView._dirreg = DirectoryView.DirectoryRegistry()
        self._dirreg = DirectoryView._dirreg
        self._dirreg.registerDirectory('one', _TESTS_PATH)
        self._dirreg.registerDirectory('two', _TESTS_PATH)
        self._dirreg.registerDirectory('three', _TESTS_PATH)
        self._dirreg.registerDirectory('four', _TESTS_PATH)

    def tearDown(self):
        from Products.CMFCore import DirectoryView

        DirectoryView._dirreg = self._olddirreg


class DirectoryViewAdapterTests(_DVRegistrySetup, NodeAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.skins \
                import DirectoryViewNodeAdapter

        return DirectoryViewNodeAdapter

    def _populate(self, obj):
        obj._dirpath = 'CMFCore/exportimport/tests/one'

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore.DirectoryView import DirectoryView

        NodeAdapterTestCase.setUp(self)
        _DVRegistrySetup.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = DirectoryView('foo_directoryview').__of__(Folder())
        self._XML = _DIRECTORYVIEW_XML

    def tearDown(self):
        _DVRegistrySetup.tearDown(self)
        NodeAdapterTestCase.tearDown(self)


class SkinsToolXMLAdapterTests(_DVRegistrySetup, BodyAdapterTestCase):

    def _getTargetClass(self):
        from Products.CMFCore.exportimport.skins import SkinsToolXMLAdapter

        return SkinsToolXMLAdapter

    def _populate(self, obj):
        from Products.CMFCore.DirectoryView import DirectoryView

        obj._setObject('foo_directoryview',
                       DirectoryView('foo_directoryview',
                                     'CMFCore/exportimport/tests/one'))
        obj.addSkinSelection('foo_path', 'one')

    def _verifyImport(self, obj):
        pass

    def setUp(self):
        import Products.CMFCore.exportimport
        from Products.CMFCore import DirectoryView
        from Products.CMFCore.SkinsTool import SkinsTool

        BodyAdapterTestCase.setUp(self)
        _DVRegistrySetup.setUp(self)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

        self._obj = SkinsTool()
        self._BODY = _SKINSTOOL_BODY

    def tearDown(self):
        _DVRegistrySetup.tearDown(self)
        BodyAdapterTestCase.tearDown(self)


class _SkinsSetup(_DVRegistrySetup, PlacelessSetup, BaseRegistryTests):

    def _initSite(self, selections={}, ids=()):
        from Products.CMFCore.DirectoryView import DirectoryView

        site = DummySite()
        fsdvs = [ (id, DirectoryView(id, 'CMFCore/exportimport/tests/%s' %
                                         id)) for id in ids ]
        site._setObject('portal_skins', DummySkinsTool(selections, fsdvs))
        site.REQUEST = 'exists'
        return site

    def setUp(self):
        PlacelessSetup.setUp(self)
        BaseRegistryTests.setUp(self)
        _DVRegistrySetup.setUp(self)
        zcml.load_config('meta.zcml', Products.Five)
        zcml.load_config('configure.zcml', Products.CMFCore.exportimport)

    def tearDown(self):
        _DVRegistrySetup.tearDown(self)
        BaseRegistryTests.tearDown(self)
        PlacelessSetup.tearDown(self)


class exportSkinsToolTests(_SkinsSetup):

    def test_empty(self):
        from Products.CMFCore.exportimport.skins import exportSkinsTool

        site = self._initSite()
        context = DummyExportContext(site)
        exportSkinsTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'skins.xml')
        self._compareDOM(text, _EMPTY_EXPORT)
        self.assertEqual(content_type, 'text/xml')

    def test_normal(self):
        from Products.CMFCore.exportimport.skins import exportSkinsTool

        _IDS = ('one', 'two', 'three')
        _PATHS = {'basic': 'one', 'fancy': 'three, two, one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        tool = site.portal_skins
        tool.default_skin = 'basic'
        tool.request_varname = 'skin_var'
        tool.allow_any = True
        tool.cookie_persistence = True

        context = DummyExportContext(site)
        exportSkinsTool(context)

        self.assertEqual(len(context._wrote), 1)
        filename, text, content_type = context._wrote[0]
        self.assertEqual(filename, 'skins.xml')
        self._compareDOM(text, _NORMAL_EXPORT)
        self.assertEqual(content_type, 'text/xml')


class importSkinsToolTests(_SkinsSetup):

    _EMPTY_EXPORT = _EMPTY_EXPORT
    _FRAGMENT1_IMPORT = _FRAGMENT1_IMPORT
    _FRAGMENT2_IMPORT = _FRAGMENT2_IMPORT
    _FRAGMENT3_IMPORT = _FRAGMENT3_IMPORT
    _FRAGMENT4_IMPORT = _FRAGMENT4_IMPORT
    _NORMAL_EXPORT = _NORMAL_EXPORT

    def test_empty_default_purge(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two', 'three')
        _PATHS = {'basic': 'one', 'fancy': 'three, two, one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 2)
        self.assertEqual(len(skins_tool.objectItems()), 3)

        context = DummyImportContext(site)
        context._files['skins.xml'] = self._EMPTY_EXPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 0)
        self.assertEqual(len(skins_tool.objectItems()), 0)

    def test_empty_explicit_purge(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two', 'three')
        _PATHS = {'basic': 'one', 'fancy': 'three, two, one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 2)
        self.assertEqual(len(skins_tool.objectItems()), 3)

        context = DummyImportContext(site, True)
        context._files['skins.xml'] = self._EMPTY_EXPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 0)
        self.assertEqual(len(skins_tool.objectItems()), 0)

    def test_empty_skip_purge(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two', 'three')
        _PATHS = {'basic': 'one', 'fancy': 'three, two, one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 2)
        self.assertEqual(len(skins_tool.objectItems()), 3)

        context = DummyImportContext(site, False)
        context._files['skins.xml'] = self._EMPTY_EXPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 2)
        self.assertEqual(len(skins_tool.objectItems()), 3)

    def test_normal(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        site = self._initSite()
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 0)
        self.assertEqual(len(skins_tool.objectItems()), 0)

        context = DummyImportContext(site)
        context._files['skins.xml'] = self._NORMAL_EXPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "basic")
        self.assertEqual(skins_tool.request_varname, "skin_var")
        self.failUnless(skins_tool.allow_any)
        self.failUnless(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        self.assertEqual(len(skins_tool.getSkinPaths()), 2)
        self.assertEqual(len(skins_tool.objectItems()), 3)

    def test_fragment_skip_purge(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two')
        _PATHS = {'basic': 'one', 'fancy': 'two,one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one'))
        self.assertEqual(skin_paths[1], ('fancy', 'two,one'))
        self.assertEqual(len(skins_tool.objectItems()), 2)

        context = DummyImportContext(site, False)
        context._files['skins.xml'] = self._FRAGMENT1_IMPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one,three'))
        self.assertEqual(skin_paths[1], ('fancy', 'three,two,one'))
        self.assertEqual(len(skins_tool.objectItems()), 3)

        context._files['skins.xml'] = self._FRAGMENT2_IMPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one,three,four'))
        self.assertEqual(skin_paths[1], ('fancy', 'three,four,two,one'))
        self.assertEqual(len(skins_tool.objectItems()), 4)

    def test_fragment3_skip_purge(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two')
        _PATHS = {'basic': 'one', 'fancy': 'two,one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        self.failIf(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one'))
        self.assertEqual(skin_paths[1], ('fancy', 'two,one'))
        self.assertEqual(len(skins_tool.objectItems()), 2)

        context = DummyImportContext(site, False)
        context._files['skins.xml'] = self._FRAGMENT3_IMPORT
        importSkinsTool(context)

        self.assertEqual(skins_tool.default_skin, "default_skin")
        self.assertEqual(skins_tool.request_varname, "request_varname")
        self.failIf(skins_tool.allow_any)
        self.failIf(skins_tool.cookie_persistence)
        self.failUnless(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'three,one,four'))
        self.assertEqual(skin_paths[1],
                          ('fancy', 'three,two,one,four'))
        self.assertEqual(len(skins_tool.objectItems()), 4)

    def test_fragment4_removal(self):
        from Products.CMFCore.exportimport.skins import importSkinsTool

        _IDS = ('one', 'two')
        _PATHS = {'basic': 'one', 'fancy': 'two,one'}

        site = self._initSite(selections=_PATHS, ids=_IDS)
        skins_tool = site.portal_skins

        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one'))
        self.assertEqual(skin_paths[1], ('fancy', 'two,one'))
        self.assertEqual(len(skins_tool.objectItems()), 2)

        context = DummyImportContext(site, False)
        context._files['skins.xml'] = self._FRAGMENT3_IMPORT
        importSkinsTool(context)

        self.failUnless(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'three,one,four'))
        self.assertEqual(skin_paths[1], ('fancy', 'three,two,one,four'))
        self.assertEqual(len(skins_tool.objectItems()), 4)

        context = DummyImportContext(site, False)
        context._files['skins.xml'] = self._FRAGMENT4_IMPORT

        importSkinsTool(context)

        self.failUnless(site._skin_setup_called)
        skin_paths = skins_tool.getSkinPaths()
        self.assertEqual(len(skin_paths), 2)
        self.assertEqual(skin_paths[0], ('basic', 'one,four'))
        self.assertEqual(skin_paths[1], ('fancy', 'two,one,four'))
        self.assertEqual(len(skins_tool.objectItems()), 4)


class importSkinsToolV1Tests(importSkinsToolTests):

    _EMPTY_EXPORT = _EMPTY_EXPORT
    _FRAGMENT1_IMPORT = _FRAGMENT1_IMPORT_V1
    _FRAGMENT2_IMPORT = _FRAGMENT2_IMPORT_V1
    _FRAGMENT3_IMPORT = _FRAGMENT3_IMPORT_V1
    _FRAGMENT4_IMPORT = _FRAGMENT4_IMPORT_V1
    _NORMAL_EXPORT = _NORMAL_EXPORT


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(DirectoryViewAdapterTests),
        unittest.makeSuite(SkinsToolXMLAdapterTests),
        unittest.makeSuite(exportSkinsToolTests),
        unittest.makeSuite(importSkinsToolTests),
        unittest.makeSuite(importSkinsToolV1Tests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
