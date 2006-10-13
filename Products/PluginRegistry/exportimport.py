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
""" GenericSetup export / import support for PluginRegistry.

$Id: exportimport.py 40099 2005-11-14 20:48:24Z tseaver $
"""
from StringIO import StringIO

from Persistence import PersistentMapping
from zope.interface import implements

from Products.GenericSetup.interfaces import IFilesystemExporter
from Products.GenericSetup.interfaces import IFilesystemImporter
from Products.GenericSetup.content import FauxDAVRequest
from Products.GenericSetup.content import FauxDAVResponse
from Products.GenericSetup.utils import ExportConfiguratorBase
from Products.GenericSetup.utils import ImportConfiguratorBase
from Products.GenericSetup.utils import _getDottedName
from Products.GenericSetup.utils import _resolveDottedName
from Products.GenericSetup.utils import CONVERTER
from Products.GenericSetup.utils import DEFAULT
from Products.GenericSetup.utils import KEY
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from interfaces import IPluginRegistry

def _providedBy(obj, iface):
    try:
        return iface.providedBy(obj)
    except AttributeError:
        return iface.isImplementedBy(obj) # Z2 interfaces

_FILENAME = 'pluginregistry.xml'

def _getRegistry(site):
    registries = [x for x in site.objectValues()
                    if _providedBy(x, IPluginRegistry)]

    if len(registries) < 1:
        raise ValueError, 'No plugin registries'

    if len(registries) > 1:
        raise ValueError, 'Too many plugin registries'

    return registries[0]

def exportPluginRegistry(context):
    """ Export plugin registry as an XML file.

    o Designed for use as a GenericSetup export step.
    """
    registry = _getRegistry(context.getSite())
    pre = PluginRegistryExporter(registry).__of__(registry)
    xml = pre.generateXML()
    context.writeDataFile(_FILENAME, xml, 'text/xml')

    return 'Plugin registry exported.'

def _updatePluginRegistry(registry, xml, should_purge, encoding=None):

    if should_purge:

        registry._plugin_types = []
        registry._plugin_type_info = PersistentMapping()
        registry._plugins = PersistentMapping()

    pir = PluginRegistryImporter(registry, encoding)
    reg_info = pir.parseXML(xml)

    for info in reg_info['plugin_types']:
        iface = _resolveDottedName(info['interface'])
        registry._plugin_types.append(iface)
        registry._plugin_type_info[iface] = {'id': info['id'],
                                             'title': info['title'],
                                             'description': info['description'],
                                            }
        registry._plugins[iface] = tuple([x['id'] for x in info['plugins']])

def importPluginRegistry(context):
    """ Import plugin registry from an XML file.

    o Designed for use as a GenericSetup import step.
    """
    registry = _getRegistry(context.getSite())
    encoding = context.getEncoding()

    xml = context.readDataFile(_FILENAME)
    if xml is None:
        return 'Site properties: Nothing to import.'

    _updatePluginRegistry(registry, xml, context.shouldPurge(), encoding)

    return 'Plugin registry imported.'

class PluginRegistryExporter(ExportConfiguratorBase):

    def __init__(self, context, encoding=None):
        ExportConfiguratorBase.__init__(self, None, encoding)
        self.context = context

    def _getExportTemplate(self):
        return PageTemplateFile('xml/pirExport.xml', globals())

    def listPluginTypes(self):
        for info in self.context.listPluginTypeInfo():
            iface = info['interface']
            info['interface'] = _getDottedName(iface)
            info['plugins'] = self.context.listPluginIds(iface)
            yield info

class PluginRegistryImporter(ImportConfiguratorBase):

    def __init__(self, context, encoding=None):
        ImportConfiguratorBase.__init__(self, None, encoding)
        self.context = context

    def _getImportMapping(self):

        return {
          'plugin-registry':
            {'plugin-type': {KEY: 'plugin_types', DEFAULT: ()},
            },
          'plugin-type':
            {'id':          {KEY: 'id'},
             'interface':   {KEY: 'interface'},
             'title':       {KEY: 'title'},
             'description': {KEY: 'description'},
             'plugin':      {KEY: 'plugins', DEFAULT: ()}
            },
          'plugin':
            {'id':          {KEY: 'id'},
            },
         }

class PluginRegistryFileExportImportAdapter(object):
    """ Designed for ues when exporting / importing PR's within a container.
    """
    implements(IFilesystemExporter, IFilesystemImporter)

    def __init__(self, context):
        self.context = context

    def export(self, export_context, subdir, root=False):
        """ See IFilesystemExporter.
        """
        context = self.context
        pre = PluginRegistryExporter(context).__of__(context)
        xml = pre.generateXML()
        export_context.writeDataFile(_FILENAME,
                                     xml,
                                     'text/xml',
                                     subdir,
                                    )

    def listExportableItems(self):
        """ See IFilesystemExporter.
        """
        return ()

    def import_(self, import_context, subdir, root=False):
        """ See IFilesystemImporter.
        """
        data = import_context.readDataFile(_FILENAME, subdir)
        if data is None:
            import_context.note('SGAIFA',
                                'no pluginregistry.xml in %s' % subdir)
        else:
            request = FauxDAVRequest(BODY=data, BODYFILE=StringIO(data))
            response = FauxDAVResponse()
            _updatePluginRegistry(self.context,
                                  data,
                                  import_context.shouldPurge(),
                                  import_context.getEncoding(),
                                 )
