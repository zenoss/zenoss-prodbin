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
"""ZCTextIndex export / import support.

$Id: exportimport.py 68186 2006-05-19 11:27:24Z yuppie $
"""

from BTrees.IOBTree import IOBTree
from BTrees.Length import Length
from BTrees.OIBTree import OIBTree

from Products.GenericSetup.utils import NodeAdapterBase

from Products.ZCTextIndex.interfaces import IZCLexicon
from Products.ZCTextIndex.interfaces import IZCTextIndex
from Products.ZCTextIndex.PipelineFactory import element_factory


class ZCLexiconNodeAdapter(NodeAdapterBase):

    """Node im- and exporter for ZCTextIndex Lexicon.
    """

    __used_for__ = IZCLexicon

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('object')
        for element in self.context._pipeline:
            group, name = self._getKeys(element)
            child = self._doc.createElement('element')
            child.setAttribute('group', group)
            child.setAttribute('name', name)
            node.appendChild(child)
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        pipeline = []
        for child in node.childNodes:
            if child.nodeName == 'element':
                element = element_factory.instantiate(
                      child.getAttribute('group').encode('utf-8'),
                      child.getAttribute('name').encode('utf-8'))
                pipeline.append(element)
        self.context._pipeline = tuple(pipeline)
        #clear lexicon
        self.context._wids = OIBTree()
        self.context._words = IOBTree()
        self.context.length = Length()

    node = property(_exportNode, _importNode)

    def _getKeys(self, element):
        for group in element_factory.getFactoryGroups():
            for name, factory in element_factory._groups[group].items():
                if factory == element.__class__:
                    return group, name


class ZCTextIndexNodeAdapter(NodeAdapterBase):

    """Node im- and exporter for ZCTextIndex.
    """

    __used_for__ = IZCTextIndex

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('index')

        for value in self.context.getIndexSourceNames():
            child = self._doc.createElement('indexed_attr')
            child.setAttribute('value', value)
            node.appendChild(child)

        child = self._doc.createElement('extra')
        child.setAttribute('name', 'index_type')
        child.setAttribute('value', self.context.getIndexType())
        node.appendChild(child)

        child = self._doc.createElement('extra')
        child.setAttribute('name', 'lexicon_id')
        child.setAttribute('value', self.context.lexicon_id)
        node.appendChild(child)

        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        indexed_attrs = []
        for child in node.childNodes:
            if child.nodeName == 'indexed_attr':
                indexed_attrs.append(
                                  child.getAttribute('value').encode('utf-8'))
        self.context._indexed_attrs = indexed_attrs
        self.context.clear()

    node = property(_exportNode, _importNode)
