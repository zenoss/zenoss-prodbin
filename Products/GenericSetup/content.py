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
"""Filesystem exporter / importer adapters.

$Id: content.py 66587 2006-04-06 10:47:06Z yuppie $
"""

from csv import reader
from csv import register_dialect
from csv import writer
from ConfigParser import ConfigParser
import re
from StringIO import StringIO

from zope.component import queryAdapter
from zope.interface import implements
from zope.interface import directlyProvides

from interfaces import IContentFactory
from interfaces import IContentFactoryName
from interfaces import IFilesystemExporter
from interfaces import IFilesystemImporter
from interfaces import IINIAware
from interfaces import ISetupTool
from utils import _getDottedName
from utils import _resolveDottedName

#
#   setup_tool handlers
#
def exportSiteStructure(context):
    IFilesystemExporter(context.getSite()).export(context, 'structure', True)

def importSiteStructure(context):
    IFilesystemImporter(context.getSite()).import_(context, 'structure', True)


#
#   Filesystem export/import adapters
#
class FolderishExporterImporter(object):
    """ Tree-walking exporter / importer for "folderish" types.

    Folderish instances are mapped to directories within the 'structure'
    portion of the profile, where the folder's relative path within the site
    corresponds to the path of its directory under 'structure'.

    The subobjects of a folderish instance are enumerated in the '.objects'
    file in the corresponding directory.  This file is a CSV file, with one
    row per subobject, with the following wtructure::

     "<subobject id>","<subobject portal_type>"

    Subobjects themselves are represented as individual files or
    subdirectories within the parent's directory.
    """

    implements(IFilesystemExporter, IFilesystemImporter)

    def __init__(self, context):
        self.context = context

    def listExportableItems(self):
        """ See IFilesystemExporter.
        """
        exportable = self.context.objectItems()
        exportable = [x for x in exportable
                        if not ISetupTool.providedBy(x[1])]
        exportable = [x + (IFilesystemExporter(x[1], None),)
                        for x in exportable]
        return exportable

    def export(self, export_context, subdir, root=False):
        """ See IFilesystemExporter.
        """
        context = self.context

        if not root:
            subdir = '%s/%s' % (subdir, context.getId())

        exportable = self.listExportableItems()

        stream = StringIO()
        csv_writer = writer(stream)

        for object_id, object, adapter in exportable:

            factory_namer = IContentFactoryName(object, None)
            if factory_namer is None:
                factory_name = _getDottedName(object.__class__)
            else:
                factory_name = factory_namer()

            csv_writer.writerow((object_id, factory_name))

        export_context.writeDataFile('.objects',
                                     text=stream.getvalue(),
                                     content_type='text/comma-separated-values',
                                     subdir=subdir,
                                    )

        prop_adapter = IINIAware(context, None)

        if prop_adapter is not None:
            export_context.writeDataFile('.properties',
                                         text=prop_adapter.as_ini(),
                                         content_type='text/plain',
                                         subdir=subdir,
                                        )

        for object_id, object, adapter in exportable:
            if adapter is not None:
                adapter.export(export_context, subdir)

    def import_(self, import_context, subdir, root=False):
        """ See IFilesystemImporter.
        """
        context = self.context
        if not root:
            subdir = '%s/%s' % (subdir, context.getId())

        prop_adapter = IINIAware(context, None)

        if prop_adapter is not None:
            prop_text = import_context.readDataFile('.properties',
                                                    subdir=subdir,
                                                   )
            if prop_text is not None:
                prop_adapter.put_ini(prop_text)

        preserve = import_context.readDataFile('.preserve', subdir)
        must_preserve = self._mustPreserve()

        prior = context.objectIds()

        if not preserve:
            preserve = []
        else:
            preserve = _globtest(preserve, prior)

        preserve.extend([x[0] for x in must_preserve])

        for id in prior:
            if id not in preserve:
                context._delObject(id)

        objects = import_context.readDataFile('.objects', subdir)
        if objects is None:
            return

        dialect = 'excel'
        stream = StringIO(objects)

        rowiter = reader(stream, dialect)

        existing = context.objectIds()

        for object_id, type_name in rowiter:

            if object_id not in existing:
                object = self._makeInstance(object_id, type_name,
                                            subdir, import_context)
                if object is None:
                    logger = import_context.getLogger('SFWA')
                    logger.warning("Couldn't make instance: %s/%s" %
                                   (subdir, object_id))
                    continue

            wrapped = context._getOb(object_id)

            IFilesystemImporter(wrapped).import_(import_context, subdir)

    def _makeInstance(self, instance_id, type_name, subdir, import_context):

        context = self.context
        class _OldStyleClass:
            pass

        if '.' in type_name:

            factory = _resolveDottedName(type_name)

            if getattr(factory, '__bases__', None) is not None:

                def _factory(instance_id,
                             container=self.context,
                             klass=factory):
                    try:
                        instance = klass(instance_id)
                    except (TypeError, ValueError):
                        instance = klass()
                    instance._setId(instance_id)
                    container._setObject(instance_id, instance)

                    return instance

                factory = _factory

        else:
            factory = queryAdapter(self.context,
                                   IContentFactory,
                                   name=type_name,
                                   )
        if factory is None:
            return None

        try:
            instance = factory(instance_id)
        except ValueError: # invalid type
            return None

        if context._getOb(instance_id, None) is None:
            context._setObject(instance_id, instance) 

        return context._getOb(instance_id)

    def _mustPreserve(self):
        return [x for x in self.context.objectItems()
                        if ISetupTool.providedBy(x[1])]
 

def _globtest(globpattern, namelist):
    """ Filter names in 'namelist', returning those which match 'globpattern'.
    """
    import re
    pattern = globpattern.replace(".", r"\.")       # mask dots
    pattern = pattern.replace("*", r".*")           # change glob sequence
    pattern = pattern.replace("?", r".")            # change glob char
    pattern = '|'.join(pattern.split())             # 'or' each line

    compiled = re.compile(pattern)

    return filter(compiled.match, namelist)


class CSVAwareFileAdapter(object):
    """ Adapter for content whose "natural" representation is CSV.
    """
    implements(IFilesystemExporter, IFilesystemImporter)

    def __init__(self, context):
        self.context = context

    def export(self, export_context, subdir, root=False):
        """ See IFilesystemExporter.
        """
        export_context.writeDataFile('%s.csv' % self.context.getId(),
                                     self.context.as_csv(),
                                     'text/comma-separated-values',
                                     subdir,
                                    )

    def listExportableItems(self):
        """ See IFilesystemExporter.
        """
        return ()

    def import_(self, import_context, subdir, root=False):
        """ See IFilesystemImporter.
        """
        cid = self.context.getId()
        data = import_context.readDataFile('%s.csv' % cid, subdir)
        if data is None:
            logger = import_context.getLogger('CSAFA')
            logger.info('no .csv file for %s/%s' % (subdir, cid))
        else:
            stream = StringIO(data)
            self.context.put_csv(stream)

class INIAwareFileAdapter(object):
    """ Exporter/importer for content whose "natural" representation is an
        '.ini' file.
    """
    implements(IFilesystemExporter, IFilesystemImporter)

    def __init__(self, context):
        self.context = context

    def export(self, export_context, subdir, root=False):
        """ See IFilesystemExporter.
        """
        export_context.writeDataFile('%s.ini' % self.context.getId(),
                                     self.context.as_ini(),
                                     'text/plain',
                                     subdir,
                                    )

    def listExportableItems(self):
        """ See IFilesystemExporter.
        """
        return ()

    def import_(self, import_context, subdir, root=False):
        """ See IFilesystemImporter.
        """
        cid = self.context.getId()
        data = import_context.readDataFile('%s.ini' % cid, subdir)
        if data is None:
            logger = import_context.getLogger('SGAIFA')
            logger.info('no .ini file for %s/%s' % (subdir, cid))
        else:
            self.context.put_ini(data)

class SimpleINIAware(object):
    """ Exporter/importer for content which doesn't know from INI.
    """
    implements(IINIAware,)

    def __init__(self, context):
        self.context = context

    def getId(self):
        return self.context.getId()

    def as_ini(self):
        """
        """
        context = self.context
        parser = ConfigParser()
        stream = StringIO()
        for k, v in context.propertyItems():
            parser.set('DEFAULT', k, str(v))
        parser.write(stream)
        return stream.getvalue()

    def put_ini(self, text):
        """
        """
        context = self.context
        parser = ConfigParser()
        parser.readfp(StringIO(text))
        for option, value in parser.defaults().items():
            prop_type = context.getPropertyType(option)
            if prop_type is None:
                context._setProperty(option, value, 'string')
            else:
                context._updateProperty(option, value)

class FauxDAVRequest:

    def __init__(self, **kw):
        self._data = {}
        self._headers = {}
        self._data.update(kw)

    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    def get_header(self, key, default=None):
        return self._headers.get(key, default)

class FauxDAVResponse:
    def setHeader(self, key, value, lock=False):
        pass  # stub this out to mollify webdav.Resource
    def setStatus(self, value, reason=None):
        pass  # stub this out to mollify webdav.Resource

class DAVAwareFileAdapter(object):
    """ Exporter/importer for content who handle their own FTP / DAV PUTs.
    """
    implements(IFilesystemExporter, IFilesystemImporter)

    def __init__(self, context):
        self.context = context

    def _getFileName(self):
        """ Return the name under which our file data is stored.
        """
        return '%s' % self.context.getId()

    def export(self, export_context, subdir, root=False):
        """ See IFilesystemExporter.
        """
        export_context.writeDataFile(self._getFileName(),
                                     self.context.manage_FTPget(),
                                     'text/plain',
                                     subdir,
                                    )

    def listExportableItems(self):
        """ See IFilesystemExporter.
        """
        return ()

    def import_(self, import_context, subdir, root=False):
        """ See IFilesystemImporter.
        """
        cid = self.context.getId()
        data = import_context.readDataFile(self._getFileName(), subdir)
        if data is None:
            logger = import_context.getLogger('SGAIFA')
            logger.info('no .ini file for %s/%s' % (subdir, cid))
        else:
            request = FauxDAVRequest(BODY=data, BODYFILE=StringIO(data))
            response = FauxDAVResponse()
            self.context.PUT(request, response)
