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
"""Content type registry xml adapters and setup handlers.

$Id: contenttyperegistry.py 40087 2005-11-13 19:55:09Z yuppie $
"""

from Products.GenericSetup.utils import exportObjects
from Products.GenericSetup.utils import importObjects
from Products.GenericSetup.utils import XMLAdapterBase

from Products.CMFCore.interfaces import IContentTypeRegistry
from Products.CMFCore.utils import getToolByName


class ContentTypeRegistryXMLAdapter(XMLAdapterBase):

    """XML im- and exporter for ContentTypeRegistry.
    """

    __used_for__ = IContentTypeRegistry

    _LOGGER_ID = 'contenttypes'

    name = 'contenttyperegistry'

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('object')
        node.appendChild(self._extractPredicates())

        self._logger.info('Content type registry exported.')
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        if self.environ.shouldPurge():
            self._purgePredicates()

        self._initPredicates(node)

        self._logger.info('Content type registry imported.')

    def _extractPredicates(self):
        fragment = self._doc.createDocumentFragment()
        for predicate_id, info in self.context.listPredicates():
            child = self._doc.createElement('predicate')
            child.setAttribute('name', predicate_id)
            child.setAttribute('predicate_type', info[0].PREDICATE_TYPE)
            child.setAttribute('content_type_name', info[1])
            for argument in self._crackArgs(info[0]):
                sub = self._doc.createElement('argument')
                sub.setAttribute('value', argument)
                child.appendChild(sub)
            fragment.appendChild(child)
        return fragment

    def _purgePredicates(self):
        self.context.__init__()

    def _initPredicates(self, node):
        for child in node.childNodes:
            if child.nodeName != 'predicate':
                continue
            parent = self.context

            predicate_id = str(child.getAttribute('name'))
            if not predicate_id:
                # BBB: for CMF 1.5 profiles
                predicate_id = str(child.getAttribute('predicate_id'))
            predicate_type = str(child.getAttribute('predicate_type'))
            content_type_name = str(child.getAttribute('content_type_name'))
            if predicate_id not in parent.predicate_ids:
                parent.addPredicate(predicate_id, predicate_type)

            arguments = []
            for sub in child.childNodes:
                if sub.nodeName != 'argument':
                    continue
                arguments.append(str(sub.getAttribute('value')))
            parent.getPredicate(predicate_id).edit(*arguments)
            parent.assignTypeName(predicate_id, content_type_name)

    _KNOWN_PREDICATE_TYPES = {
        'major_minor': lambda x: (','.join(x.major or ()),
                                  ','.join(x.minor or ())),
        'extension': lambda x: (','.join(x.extensions or ()),),
        'mimetype_regex': lambda x: (x.pattern and x.pattern.pattern or '',),
        'name_regex': lambda x: (x.pattern and x.pattern.pattern or '',),
    }

    def _crackArgs(self, predicate):
        cracker = self._KNOWN_PREDICATE_TYPES.get(predicate.PREDICATE_TYPE)
        if cracker is not None:
            return cracker(predicate)
        return ()  # XXX:  raise?


def importContentTypeRegistry(context):
    """Import content type registry settings from an XML file.
    """
    site = context.getSite()
    tool = getToolByName(site, 'content_type_registry')

    importObjects(tool, '', context)

def exportContentTypeRegistry(context):
    """Export content type registry settings as an XML file.
    """
    site = context.getSite()
    tool = getToolByName(site, 'content_type_registry', None)
    if tool is None:
        logger = context.getLogger('contenttypes')
        logger.info('Nothing to export.')
        return

    exportObjects(tool, '', context)
