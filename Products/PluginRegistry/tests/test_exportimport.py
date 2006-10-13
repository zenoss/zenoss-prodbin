##############################################################################
#
# Copyright (c) 2005 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
""" Unit tests for GenericSetup-based export / import of PluginRegistry.

$Id: test_exportimport.py 68733 2006-06-18 11:44:00Z jens $
"""
import unittest

try:
    import Products.GenericSetup
except ImportError:  # No GenericSetup, so no tests

    print 'XXXX:  No GenericSetup!'
    def test_suite():
        return unittest.TestSuite()

else:
    from Products.GenericSetup.tests.common import BaseRegistryTests
    from Products.GenericSetup.tests.common import DummyExportContext
    from Products.GenericSetup.tests.common import DummyImportContext
    from Products.GenericSetup.utils import _getDottedName

    from zope.interface import Interface
    try:
        from zope.app.testing.placelesssetup import PlacelessSetup
    except ImportError:
        # BBB for Zope 2.8
        from zope.app.tests.placelesssetup import PlacelessSetup

    class IFoo(Interface):
        pass

    class IBar(Interface):
        pass

    _EMPTY_PLUGINREGISTRY_EXPORT = """\
<?xml version="1.0"?>
<plugin-registry>
</plugin-registry>
"""

    _PLUGIN_TYPE_INFO = (
      ( IFoo
      , 'IFoo'
      , 'foo'
      , "Some plugin interface"
      )
    , ( IBar
      , 'IBar'
      , 'bar'
      , "Another plugin interface"
      )
    )

    _NO_PLUGINS_PLUGINREGISTRY_EXPORT = """\
<?xml version="1.0"?>
<plugin-registry>
 <plugin-type
    id="IFoo"
    interface="%s"
    title="foo"
    description="Some plugin interface">
 </plugin-type>
 <plugin-type
    id="IBar"
    interface="%s"
    title="bar"
    description="Another plugin interface">
 </plugin-type>
</plugin-registry>
""" % (_getDottedName(IFoo), _getDottedName(IBar))

    _NORMAL_PLUGINREGISTRY_EXPORT = """\
<?xml version="1.0"?>
<plugin-registry>
 <plugin-type
    id="IFoo"
    interface="%s"
    title="foo"
    description="Some plugin interface">
  <plugin id="foo_plugin_1" />
  <plugin id="foo_plugin_2" />
 </plugin-type>
 <plugin-type
    id="IBar"
    interface="%s"
    title="bar"
    description="Another plugin interface">
 </plugin-type>
</plugin-registry>
""" % (_getDottedName(IFoo), _getDottedName(IBar))

    class _TestBase(PlacelessSetup, BaseRegistryTests):

        def _initRegistry(self, plugin_type_info=(), plugins={}):
            from OFS.Folder import Folder
            from OFS.SimpleItem import SimpleItem
            from Products.PluginRegistry.PluginRegistry import PluginRegistry

            app = Folder()
            app.getPhysicalPath = lambda: ()
            app.getPhysicalRoot = lambda: app

            app._setObject('foo_plugin_1', SimpleItem())
            app._setObject('foo_plugin_2', SimpleItem())

            registry = PluginRegistry(plugin_type_info)
            registry._plugins = {} # it is usually lazy

            for plugin_type, registered in plugins.items():
                registry._plugins[plugin_type] = registered

            app._setObject('plugin_registry', registry)
            registry = app._getOb('plugin_registry')
            return app, registry

    class PluginRegistryExporterTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluginRegistry.exportimport \
                import PluginRegistryExporter
            return PluginRegistryExporter

        def test_empty(self):

            app, registry = self._initRegistry()
            exporter = self._makeOne(registry).__of__(registry)
            xml = exporter.generateXML()

            self._compareDOM(xml, _EMPTY_PLUGINREGISTRY_EXPORT)

        def test_normal_no_plugins(self):
            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO)
            exporter = self._makeOne(registry).__of__(registry)
            xml = exporter.generateXML()

            self._compareDOM(xml, _NO_PLUGINS_PLUGINREGISTRY_EXPORT)

        def test_normal_with_plugins(self):
            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO,
                                    plugins={IFoo: ('foo_plugin_1',
                                                    'foo_plugin_2')},
                                        )
            exporter = self._makeOne(registry).__of__(registry)
            xml = exporter.generateXML()

            self._compareDOM(xml, _NORMAL_PLUGINREGISTRY_EXPORT)

    class Test_exportPluginRegistry(_TestBase):

        def test_empty(self):
            from Products.PluginRegistry.exportimport \
                import exportPluginRegistry

            app, registry = self._initRegistry()
            context = DummyExportContext(app)
            exportPluginRegistry(context)

            self.assertEqual( len(context._wrote), 1 )
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'pluginregistry.xml')
            self._compareDOM(text, _EMPTY_PLUGINREGISTRY_EXPORT)
            self.assertEqual(content_type, 'text/xml')

        def test_normal_no_plugins(self):
            from Products.PluginRegistry.exportimport \
                import exportPluginRegistry

            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO)
            context = DummyExportContext(app)
            exportPluginRegistry(context)

            self.assertEqual( len(context._wrote), 1 )
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'pluginregistry.xml')
            self._compareDOM(text, _NO_PLUGINS_PLUGINREGISTRY_EXPORT)
            self.assertEqual(content_type, 'text/xml')

        def test_normal_with_plugins(self):
            from Products.PluginRegistry.exportimport \
                import exportPluginRegistry

            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO,
                                    plugins={IFoo: ('foo_plugin_1',
                                                    'foo_plugin_2')},
                                        )
            context = DummyExportContext(app)
            exportPluginRegistry(context)

            self.assertEqual( len(context._wrote), 1 )
            filename, text, content_type = context._wrote[0]
            self.assertEqual(filename, 'pluginregistry.xml')
            self._compareDOM(text, _NORMAL_PLUGINREGISTRY_EXPORT)
            self.assertEqual(content_type, 'text/xml')

    class PluginRegistryImporterTests(_TestBase):

        def _getTargetClass(self):
            from Products.PluginRegistry.exportimport \
                import PluginRegistryImporter
            return PluginRegistryImporter

        def test_parseXML_empty(self):

            app, registry = self._initRegistry()
            importer = self._makeOne(registry).__of__(registry)
            reg_info = importer.parseXML(_EMPTY_PLUGINREGISTRY_EXPORT)

            self.assertEqual( len( reg_info['plugin_types'] ), 0 )

        def test_parseXML_normal_no_plugins(self):

            app, registry = self._initRegistry()
            importer = self._makeOne(registry).__of__(registry)
            reg_info = importer.parseXML(_NO_PLUGINS_PLUGINREGISTRY_EXPORT)

            self.assertEqual( len( reg_info['plugin_types'] ), 2 )

            info = reg_info['plugin_types'][0]
            self.assertEqual(info['id'], 'IFoo')
            self.assertEqual(info['interface'], _getDottedName(IFoo))
            self.assertEqual(info['title'], 'foo')
            self.assertEqual(info['description'], 'Some plugin interface')
            self.assertEqual(len( info['plugins'] ), 0)

            info = reg_info['plugin_types'][1]
            self.assertEqual(info['id'], 'IBar')
            self.assertEqual(info['interface'], _getDottedName(IBar))
            self.assertEqual(info['title'], 'bar')
            self.assertEqual(info['description'], 'Another plugin interface')
            self.assertEqual(len( info['plugins'] ), 0 )

        def test_parseXML_normal_with_plugins(self):

            app, registry = self._initRegistry()
            importer = self._makeOne(registry).__of__(registry)
            reg_info = importer.parseXML(_NORMAL_PLUGINREGISTRY_EXPORT)

            self.assertEqual(len(reg_info['plugin_types'] ), 2 )

            info = reg_info['plugin_types'][0]
            self.assertEqual(info['id'], 'IFoo')
            self.assertEqual(info['interface'], _getDottedName(IFoo))
            self.assertEqual(info['title'], 'foo')
            self.assertEqual(info['description'], 'Some plugin interface')
            plugins = info['plugins']
            self.assertEqual(len(plugins), 2)
            self.assertEqual(plugins[0]['id'], 'foo_plugin_1')
            self.assertEqual(plugins[1]['id'], 'foo_plugin_2')

            info = reg_info['plugin_types'][1]
            self.assertEqual(info['id'], 'IBar')
            self.assertEqual(info['interface'], _getDottedName(IBar))
            self.assertEqual(info['title'], 'bar')
            self.assertEqual(info['description'], 'Another plugin interface')
            self.assertEqual(len(info['plugins']), 0 )

    class Test_importPluginRegistry(_TestBase):

        def test_empty_default_purge(self):
            from Products.PluginRegistry.exportimport \
                import importPluginRegistry

            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO,
                                    plugins={IFoo: ('foo_plugin_1',
                                                    'foo_plugin_2')},
                                   )

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)
            self.assertEqual(len(registry.listPlugins(IFoo)), 2)
            self.assertEqual(len(registry.listPlugins(IBar)), 0)

            context = DummyImportContext(app)
            context._files['pluginregistry.xml'] = _EMPTY_PLUGINREGISTRY_EXPORT

            importPluginRegistry(context)

            self.assertEqual(len(registry.listPluginTypeInfo()), 0)
            self.assertRaises(KeyError, registry.listPlugins, IFoo)
            self.assertRaises(KeyError, registry.listPlugins, IBar)

        def test_empty_explicit_purge(self):
            from Products.PluginRegistry.exportimport \
                import importPluginRegistry

            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO,
                                    plugins={IFoo: ('foo_plugin_1',
                                                    'foo_plugin_2')},
                                   )

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)
            self.assertEqual(len(registry.listPlugins(IFoo)), 2)
            self.assertEqual(len(registry.listPlugins(IBar)), 0)

            context = DummyImportContext(app, True)
            context._files['pluginregistry.xml'] = _EMPTY_PLUGINREGISTRY_EXPORT

            importPluginRegistry(context)

            self.assertEqual(len(registry.listPluginTypeInfo()), 0)
            self.assertRaises(KeyError, registry.listPlugins, IFoo)
            self.assertRaises(KeyError, registry.listPlugins, IBar)

        def test_empty_skip_purge(self):
            from Products.PluginRegistry.exportimport \
                import importPluginRegistry

            app, registry = self._initRegistry(
                                    plugin_type_info=_PLUGIN_TYPE_INFO,
                                    plugins={IFoo: ('foo_plugin_1',
                                                    'foo_plugin_2')},
                                   )

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)
            self.assertEqual(len(registry.listPlugins(IFoo)), 2)
            self.assertEqual(len(registry.listPlugins(IBar)), 0)

            context = DummyImportContext(app, False)
            context._files['pluginregistry.xml'] = _EMPTY_PLUGINREGISTRY_EXPORT

            importPluginRegistry(context)

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)
            self.assertEqual(len(registry.listPlugins(IFoo)), 2)
            self.assertEqual(len(registry.listPlugins(IBar)), 0)

        def test_normal_no_plugins(self):
            from Products.PluginRegistry.exportimport \
                import importPluginRegistry

            app, registry = self._initRegistry()

            self.assertEqual(len(registry.listPluginTypeInfo()), 0)
            self.assertRaises(KeyError, registry.listPlugins, IFoo)
            self.assertRaises(KeyError, registry.listPlugins, IBar)

            context = DummyImportContext(app, False)
            context._files['pluginregistry.xml'
                          ] = _NO_PLUGINS_PLUGINREGISTRY_EXPORT

            importPluginRegistry(context)

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)

            info = registry.listPluginTypeInfo()[0]
            self.assertEqual(info['id'], 'IFoo')
            self.assertEqual(info['title'], 'foo')
            self.assertEqual(info['description'], 'Some plugin interface')

            info = registry.listPluginTypeInfo()[1]
            self.assertEqual(info['id'], 'IBar')
            self.assertEqual(info['title'], 'bar')
            self.assertEqual(info['description'], 'Another plugin interface')

            self.assertEqual(len(registry.listPlugins(IFoo)), 0)
            self.assertEqual(len(registry.listPlugins(IBar)), 0)

        def test_normal_with_plugins(self):
            from Products.PluginRegistry.exportimport \
                import importPluginRegistry

            app, registry = self._initRegistry()

            self.assertEqual(len(registry.listPluginTypeInfo()), 0)
            self.assertRaises(KeyError, registry.listPlugins, IFoo)
            self.assertRaises(KeyError, registry.listPlugins, IBar)

            context = DummyImportContext(app, False)
            context._files['pluginregistry.xml'
                          ] = _NORMAL_PLUGINREGISTRY_EXPORT

            importPluginRegistry(context)

            self.assertEqual(len(registry.listPluginTypeInfo()), 2)

            info = registry.listPluginTypeInfo()[0]
            self.assertEqual(info['id'], 'IFoo')
            self.assertEqual(info['title'], 'foo')
            self.assertEqual(info['description'], 'Some plugin interface')

            info = registry.listPluginTypeInfo()[1]
            self.assertEqual(info['id'], 'IBar')
            self.assertEqual(info['title'], 'bar')
            self.assertEqual(info['description'], 'Another plugin interface')

            self.assertEqual(len(registry.listPlugins(IFoo)), 2)
            plugins = registry.listPlugins(IFoo)
            self.assertEqual(plugins[0][0], 'foo_plugin_1')
            self.assertEqual(plugins[0][1], app._getOb('foo_plugin_1'))
            self.assertEqual(plugins[1][0], 'foo_plugin_2')
            self.assertEqual(plugins[1][1], app._getOb('foo_plugin_2'))

            self.assertEqual(len(registry.listPlugins(IBar)), 0)

    def test_suite():
        return unittest.TestSuite((
            unittest.makeSuite( PluginRegistryExporterTests ),
            unittest.makeSuite( PluginRegistryImporterTests ),
            unittest.makeSuite( Test_exportPluginRegistry ),
            unittest.makeSuite( Test_importPluginRegistry ),
           ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')

