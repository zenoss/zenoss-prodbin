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
"""OFSP export / import support.

$Id: exportimport.py 68593 2006-06-12 07:48:32Z yuppie $
"""

from Products.GenericSetup.utils import XMLAdapterBase
from Products.GenericSetup.utils import ObjectManagerHelpers
from Products.GenericSetup.utils import PropertyManagerHelpers

from OFS.interfaces import IFolder


class FolderXMLAdapter(XMLAdapterBase, ObjectManagerHelpers,
                       PropertyManagerHelpers):

    """XML im- and exporter for Folder.
    """

    __used_for__ = IFolder

    _LOGGER_ID = 'ofs'

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('object')
        node.appendChild(self._extractProperties())
        node.appendChild(self._extractObjects())

        self._logger.info('Folder exported.')
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        if self.environ.shouldPurge():
            self._purgeProperties()
            self._purgeObjects()

        self._initProperties(node)
        self._initObjects(node)

        self._logger.info('Folder imported.')

    def _exportBody(self):
        """Export the object as a file body.
        """
        if not self.context.meta_type in ('Folder', 'Folder (Ordered)'):
            return None

        return XMLAdapterBase._exportBody(self)

    body = property(_exportBody, XMLAdapterBase._importBody)
