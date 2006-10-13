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
""" GenericSetup product utilities

$Id: utils.py 68594 2006-06-12 07:59:54Z yuppie $
"""

import os
import sys
from inspect import getdoc
from xml.dom.minidom import _nssplit
from xml.dom.minidom import Document
from xml.dom.minidom import Element
from xml.dom.minidom import Node
from xml.dom.minidom import parseString
from xml.sax.handler import ContentHandler
from xml.parsers.expat import ExpatError

import Products
from AccessControl import ClassSecurityInfo
from Acquisition import Implicit
from Globals import InitializeClass
from Globals import package_home
try:
    from OFS.interfaces import IOrderedContainer
except:
    #BBB: for Zope 2.8
    from Products.Five.bbb.OFS_interfaces import IOrderedContainer
from cgi import escape
from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.interface import implementsOnly
from zope.interface import providedBy

from exceptions import BadRequest
from interfaces import IBody
from interfaces import INode
from interfaces import ISetupContext
from interfaces import ISetupTool
from permissions import ManagePortal


_pkgdir = package_home( globals() )
_wwwdir = os.path.join( _pkgdir, 'www' )
_xmldir = os.path.join( _pkgdir, 'xml' )

# Please note that these values may change. Always import 
# the values from here instead of using the values directly.
CONVERTER, DEFAULT, KEY = 1, 2, 3
I18NURI = 'http://xml.zope.org/namespaces/i18n'


def _getDottedName( named ):

    if isinstance( named, basestring ):
        return str( named )

    try:
        return '%s.%s' % ( named.__module__, named.__name__ )
    except AttributeError:
        raise ValueError, 'Cannot compute dotted name: %s' % named

def _resolveDottedName( dotted ):

    __traceback_info__ = dotted

    parts = dotted.split( '.' )

    if not parts:
        raise ValueError, "incomplete dotted name: %s" % dotted

    parts_copy = parts[:]

    while parts_copy:
        try:
            module = __import__( '.'.join( parts_copy ) )
            break

        except ImportError:
            # Reraise if the import error was caused inside the imported file
            if sys.exc_info()[2].tb_next is not None: raise

            del parts_copy[ -1 ]

            if not parts_copy:
                raise

    parts = parts[ 1: ] # Funky semantics of __import__'s return value

    obj = module

    for part in parts:
        obj = getattr( obj, part )

    return obj

def _extractDocstring( func, default_title, default_description ):

    try:
        doc = getdoc( func )
        lines = doc.split( '\n' )

    except AttributeError:

        title = default_title
        description = default_description

    else:
        title = lines[ 0 ]

        if len( lines ) > 1 and lines[ 1 ].strip() == '':
            del lines[ 1 ]

        description = '\n'.join( lines[ 1: ] )

    return title, description


class HandlerBase( ContentHandler ):

    _encoding = None
    _MARKER = object()

    def _extract( self, attrs, key, default=None ):

        result = attrs.get( key, self._MARKER )

        if result is self._MARKER:
            return default

        return self._encode( result )

    def _extractBoolean( self, attrs, key, default ):

        result = attrs.get( key, self._MARKER )

        if result is self._MARKER:
            return default

        result = result.lower()
        return result in ( '1', 'yes', 'true' )

    def _encode( self, content ):

        if self._encoding is None:
            return content

        return content.encode( self._encoding )


class ImportConfiguratorBase(Implicit):
    """ Synthesize data from XML description.
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    def __init__(self, site, encoding=None):

        self._site = site
        self._encoding = encoding

    security.declareProtected(ManagePortal, 'parseXML')
    def parseXML(self, xml):
        """ Pseudo API.
        """
        reader = getattr(xml, 'read', None)

        if reader is not None:
            xml = reader()

        dom = parseString(xml)
        root = dom.documentElement

        return self._extractNode(root)

    def _extractNode(self, node):

        nodes_map = self._getImportMapping()
        if node.nodeName not in nodes_map:
            nodes_map = self._getSharedImportMapping()
            if node.nodeName not in nodes_map:
                raise ValueError('Unknown node: %s' % node.nodeName)
        node_map = nodes_map[node.nodeName]
        info = {}

        for name, val in node.attributes.items():
            key = node_map[name].get( KEY, str(name) )
            val = self._encoding and val.encode(self._encoding) or val
            info[key] = val

        for child in node.childNodes:
            name = child.nodeName

            if name == '#comment':
                continue

            if not name == '#text':
                key = node_map[name].get(KEY, str(name) )
                info[key] = info.setdefault( key, () ) + (
                                                    self._extractNode(child),)

            elif '#text' in node_map:
                key = node_map['#text'].get(KEY, 'value')
                val = child.nodeValue.lstrip()
                val = self._encoding and val.encode(self._encoding) or val
                info[key] = info.setdefault(key, '') + val

        for k, v in node_map.items():
            key = v.get(KEY, k)

            if DEFAULT in v and not key in info:
                if isinstance( v[DEFAULT], basestring ):
                    info[key] = v[DEFAULT] % info
                else:
                    info[key] = v[DEFAULT]

            elif CONVERTER in v and key in info:
                info[key] = v[CONVERTER]( info[key] )

            if key is None:
                info = info[key]

        return info

    def _getSharedImportMapping(self):

        return {
          'object':
            { 'i18n:domain':     {},
              'name':            {KEY: 'id'},
              'meta_type':       {},
              'insert-before':   {},
              'insert-after':    {},
              'property':        {KEY: 'properties', DEFAULT: ()},
              'object':          {KEY: 'objects', DEFAULT: ()},
              'xmlns:i18n':      {} },
          'property':
            { 'name':            {KEY: 'id'},
              '#text':           {KEY: 'value', DEFAULT: ''},
              'element':         {KEY: 'elements', DEFAULT: ()},
              'type':            {},
              'select_variable': {},
              'i18n:translate':  {} },
          'element':
            { 'value':           {KEY: None} },
          'description':
            { '#text':           {KEY: None, DEFAULT: ''} } }

    def _convertToBoolean(self, val):

        return val.lower() in ('true', 'yes', '1')

    def _convertToUnique(self, val):

        assert len(val) == 1
        return val[0]

InitializeClass(ImportConfiguratorBase)


class ExportConfiguratorBase(Implicit):
    """ Synthesize XML description.
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    def __init__(self, site, encoding=None):

        self._site = site
        self._encoding = encoding
        self._template = self._getExportTemplate()

    security.declareProtected(ManagePortal, 'generateXML')
    def generateXML(self, **kw):
        """ Pseudo API.
        """
        return self._template(**kw)

InitializeClass(ExportConfiguratorBase)


# BBB: old class mixing the two, will be removed in CMF 2.1
class ConfiguratorBase(ImportConfiguratorBase, ExportConfiguratorBase):
    """ Synthesize XML description.
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    def __init__(self, site, encoding=None):
        ImportConfiguratorBase.__init__(self, site, encoding)
        ExportConfiguratorBase.__init__(self, site, encoding)

InitializeClass(ConfiguratorBase)


class _LineWrapper:

    def __init__(self, writer, indent, addindent, newl, max):
        self._writer = writer
        self._indent = indent
        self._addindent = addindent
        self._newl = newl
        self._max = max
        self._length = 0
        self._queue = self._indent

    def queue(self, text):
        self._queue += text

    def write(self, text='', enforce=False):
        self._queue += text

        if 0 < self._length > self._max - len(self._queue):
            self._writer.write(self._newl)
            self._length = 0
            self._queue = '%s%s %s' % (self._indent, self._addindent,
                                       self._queue)

        if self._queue != self._indent:
            self._writer.write(self._queue)
            self._length += len(self._queue)
            self._queue = ''

        if 0 < self._length and enforce:
            self._writer.write(self._newl)
            self._length = 0
            self._queue = self._indent


class _Element(Element):

    """minidom element with 'pretty' XML output.
    """

    def writexml(self, writer, indent="", addindent="", newl=""):
        # indent = current indentation
        # addindent = indentation to add to higher levels
        # newl = newline string
        wrapper = _LineWrapper(writer, indent, addindent, newl, 78)
        wrapper.write('<%s' % self.tagName)

        # move 'name', 'meta_type' and 'title' to the top, sort the rest 
        attrs = self._get_attributes()
        a_names = attrs.keys()
        a_names.sort()
        if 'title' in a_names:
            a_names.remove('title')
            a_names.insert(0, 'title')
        if 'meta_type' in a_names:
            a_names.remove('meta_type')
            a_names.insert(0, 'meta_type')
        if 'name' in a_names:
            a_names.remove('name')
            a_names.insert(0, 'name')

        for a_name in a_names:
            wrapper.write()
            a_value = escape(attrs[a_name].value, quote=True)
            wrapper.queue(' %s="%s"' % (a_name, a_value))

        if self.childNodes:
            wrapper.queue('>')
            for node in self.childNodes:
                if node.nodeType == Node.TEXT_NODE:
                    data = escape(node.data)
                    textlines = data.splitlines()
                    if textlines:
                        wrapper.queue(textlines.pop(0))
                    if textlines:
                        for textline in textlines:
                            wrapper.write('', True)
                            wrapper.queue('%s%s' % (addindent, textline))
                else:
                    wrapper.write('', True)
                    node.writexml(writer, indent+addindent, addindent, newl)
            wrapper.write('</%s>' % self.tagName, True)
        else:
            wrapper.write('/>', True)


class PrettyDocument(Document):

    """minidom document with 'pretty' XML output.
    """

    def createElement(self, tagName):
        e = _Element(tagName)
        e.ownerDocument = self
        return e

    def createElementNS(self, namespaceURI, qualifiedName):
        prefix, localName = _nssplit(qualifiedName)
        e = _Element(qualifiedName, namespaceURI, prefix)
        e.ownerDocument = self
        return e

    def writexml(self, writer, indent="", addindent="", newl="",
                 encoding = None):
        if encoding is None:
            writer.write('<?xml version="1.0"?>\n')
        else:
            writer.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)
        for node in self.childNodes:
            node.writexml(writer, indent, addindent, newl)


class NodeAdapterBase(object):

    """Node im- and exporter base.
    """

    implements(INode)

    _LOGGER_ID = ''

    def __init__(self, context, environ):
        self.context = context
        self.environ = environ
        self._logger = environ.getLogger(self._LOGGER_ID)
        self._doc = PrettyDocument()

    def _getObjectNode(self, name, i18n=True):
        node = self._doc.createElement(name)
        node.setAttribute('name', self.context.getId())
        node.setAttribute('meta_type', self.context.meta_type)
        i18n_domain = getattr(self.context, 'i18n_domain', None)
        if i18n and i18n_domain:
            node.setAttributeNS(I18NURI, 'i18n:domain', i18n_domain)
            self._i18n_props = ('title', 'description')
        return node

    def _getNodeText(self, node):
        text = ''
        for child in node.childNodes:
            if child.nodeName != '#text':
                continue
            lines = [ line.lstrip() for line in child.nodeValue.splitlines() ]
            text += '\n'.join(lines)
        return text

    def _convertToBoolean(self, val):
        return val.lower() in ('true', 'yes', '1')


class BodyAdapterBase(NodeAdapterBase):

    """Body im- and exporter base.
    """

    implementsOnly(IBody)

    def _exportSimpleNode(self):
        """Export the object as a DOM node.
        """
        if ISetupTool.providedBy(self.context):
            return None
        return self._getObjectNode('object', False)

    def _importSimpleNode(self, node):
        """Import the object from the DOM node.
        """

    node = property(_exportSimpleNode, _importSimpleNode)

    def _exportBody(self):
        """Export the object as a file body.
        """
        return ''

    def _importBody(self, body):
        """Import the object from the file body.
        """

    body = property(_exportBody, _importBody)

    mime_type = 'text/plain'

    name = ''

    suffix = ''


class XMLAdapterBase(BodyAdapterBase):

    """XML im- and exporter base.
    """

    implementsOnly(IBody)

    def _exportBody(self):
        """Export the object as a file body.
        """
        self._doc.appendChild(self._exportNode())
        return self._doc.toprettyxml(' ')

    def _importBody(self, body):
        """Import the object from the file body.
        """
        try:
            dom = parseString(body)
        except ExpatError, e:
            filename = (self.filename or
                        '/'.join(self.context.getPhysicalPath()))
            raise ExpatError('%s: %s' % (filename, e))
        self._importNode(dom.documentElement)

    body = property(_exportBody, _importBody)

    mime_type = 'text/xml'

    name = ''

    suffix = '.xml'

    filename = '' # for error reporting during import


class ObjectManagerHelpers(object):

    """ObjectManager im- and export helpers.
    """

    def _extractObjects(self):
        fragment = self._doc.createDocumentFragment()
        objects = self.context.objectValues()
        if not IOrderedContainer.providedBy(self.context):
            objects = list(objects)
            objects.sort(lambda x,y: cmp(x.getId(), y.getId()))
        for obj in objects:
            exporter = queryMultiAdapter((obj, self.environ), INode)
            if exporter:
                node = exporter.node
                if node is not None:
                    fragment.appendChild(exporter.node)
        return fragment

    def _purgeObjects(self):
        for obj_id, obj in self.context.objectItems():
            if ISetupTool.providedBy(obj):
                continue
            self.context._delObject(obj_id)

    def _initObjects(self, node):
        for child in node.childNodes:
            if child.nodeName != 'object':
                continue
            if child.hasAttribute('deprecated'):
                continue
            parent = self.context

            obj_id = str(child.getAttribute('name'))
            if child.hasAttribute('remove'):
                parent._delObject(obj_id)
                continue

            if obj_id not in parent.objectIds():
                meta_type = str(child.getAttribute('meta_type'))
                __traceback_info__ = obj_id, meta_type
                for mt_info in Products.meta_types:
                    if mt_info['name'] == meta_type:
                        parent._setObject(obj_id, mt_info['instance'](obj_id))
                        break
                else:
                    raise ValueError("unknown meta_type '%s'" % meta_type)

            if child.hasAttribute('insert-before'):
                insert_before = child.getAttribute('insert-before')
                if insert_before == '*':
                    parent.moveObjectsToTop(obj_id)
                else:
                    try:
                        position = parent.getObjectPosition(insert_before)
                        if parent.getObjectPosition(obj_id) < position:
                            position -= 1
                        parent.moveObjectToPosition(obj_id, position)
                    except ValueError:
                        pass
            elif child.hasAttribute('insert-after'):
                insert_after = child.getAttribute('insert-after')
                if insert_after == '*':
                    parent.moveObjectsToBottom(obj_id)
                else:
                    try:
                        position = parent.getObjectPosition(insert_after)
                        if parent.getObjectPosition(obj_id) < position:
                            position -= 1
                        parent.moveObjectToPosition(obj_id, position+1)
                    except ValueError:
                        pass

            obj = getattr(self.context, obj_id)
            importer = queryMultiAdapter((obj, self.environ), INode)
            if importer:
                importer.node = child


class PropertyManagerHelpers(object):

    """PropertyManager im- and export helpers.
    """

    def _extractProperties(self):
        fragment = self._doc.createDocumentFragment()

        for prop_map in self.context._propertyMap():
            prop_id = prop_map['id']
            if prop_id == 'i18n_domain':
                continue

            # Don't export read-only nodes
            if 'w' not in prop_map.get('mode', 'wd'):
                continue

            node = self._doc.createElement('property')
            node.setAttribute('name', prop_id)

            prop = self.context.getProperty(prop_id)
            if isinstance(prop, (tuple, list)):
                for value in prop:
                    child = self._doc.createElement('element')
                    child.setAttribute('value', value)
                    node.appendChild(child)
            else:
                if prop_map.get('type') == 'boolean':
                    prop = str(bool(prop))
                elif not isinstance(prop, basestring):
                    prop = str(prop)
                child = self._doc.createTextNode(prop)
                node.appendChild(child)

            if 'd' in prop_map.get('mode', 'wd') and not prop_id == 'title':
                type = prop_map.get('type', 'string')
                node.setAttribute('type', type)
                select_variable = prop_map.get('select_variable', None)
                if select_variable is not None:
                    node.setAttribute('select_variable', select_variable)

            if hasattr(self, '_i18n_props') and prop_id in self._i18n_props:
                node.setAttribute('i18n:translate', '')

            fragment.appendChild(node)

        return fragment

    def _purgeProperties(self):
        for prop_map in self.context._propertyMap():
            mode = prop_map.get('mode', 'wd')
            if 'w' not in mode:
                continue
            prop_id = prop_map['id']
            if 'd' in mode and not prop_id == 'title':
                self.context._delProperty(prop_id)
            else:
                prop_type = prop_map.get('type')
                if prop_type == 'multiple selection':
                    prop_value = ()
                elif prop_type in ('int', 'float'):
                    prop_value = 0
                else:
                    prop_value = ''
                self.context._updateProperty(prop_id, prop_value)

    def _initProperties(self, node):
        obj = self.context
        if node.hasAttribute('i18n:domain'):
            i18n_domain = str(node.getAttribute('i18n:domain'))
            obj._updateProperty('i18n_domain', i18n_domain)
        for child in node.childNodes:
            if child.nodeName != 'property':
                continue
            prop_id = str(child.getAttribute('name'))
            prop_map = obj.propdict().get(prop_id, None)

            if prop_map is None:
                if child.hasAttribute('type'):
                    val = child.getAttribute('select_variable')
                    obj._setProperty(prop_id, val, child.getAttribute('type'))
                    prop_map = obj.propdict().get(prop_id, None)
                else:
                    raise ValueError("undefined property '%s'" % prop_id)

            if not 'w' in prop_map.get('mode', 'wd'):
                raise BadRequest('%s cannot be changed' % prop_id)

            elements = []
            for sub in child.childNodes:
                if sub.nodeName == 'element':
                    elements.append(sub.getAttribute('value').encode('utf-8'))

            if elements or prop_map.get('type') == 'multiple selection':
                prop_value = tuple(elements) or ()
            elif prop_map.get('type') == 'boolean':
                prop_value = self._convertToBoolean(self._getNodeText(child))
            else:
                # if we pass a *string* to _updateProperty, all other values
                # are converted to the right type
                prop_value = self._getNodeText(child).encode('utf-8')

            if not self._convertToBoolean(child.getAttribute('purge')
                                          or 'True'):
                # If the purge attribute is False, merge sequences
                prop = obj.getProperty(prop_id)
                if isinstance(prop, (tuple, list)):
                    prop_value = (tuple([p for p in prop
                                         if p not in prop_value]) +
                                  tuple(prop_value))

            obj._updateProperty(prop_id, prop_value)


def exportObjects(obj, parent_path, context):
    """ Export subobjects recursively.
    """
    exporter = queryMultiAdapter((obj, context), IBody)
    path = '%s%s' % (parent_path, obj.getId().replace(' ', '_'))
    if exporter:
        if exporter.name:
            path = '%s%s' % (parent_path, exporter.name)
        filename = '%s%s' % (path, exporter.suffix)
        body = exporter.body
        if body is not None:
            context.writeDataFile(filename, body, exporter.mime_type)

    if getattr(obj, 'objectValues', False):
        for sub in obj.objectValues():
            exportObjects(sub, path+'/', context)

def importObjects(obj, parent_path, context):
    """ Import subobjects recursively.
    """
    importer = queryMultiAdapter((obj, context), IBody)
    path = '%s%s' % (parent_path, obj.getId().replace(' ', '_'))
    __traceback_info__ = path
    if importer:
        if importer.name:
            path = '%s%s' % (parent_path, importer.name)
        filename = '%s%s' % (path, importer.suffix)
        body = context.readDataFile(filename)
        if body is None and filename == 'types.xml':
            # BBB: for CMF 1.5 profiles
            body = context.readDataFile('typestool.xml')
        if body is not None:
            importer.filename = filename # for error reporting
            importer.body = body

    if getattr(obj, 'objectValues', False):
        for sub in obj.objectValues():
            importObjects(sub, path+'/', context)
