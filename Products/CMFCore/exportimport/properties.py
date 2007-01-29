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
"""Site properties xml adapters and setup handlers.

$Id: properties.py 39947 2005-11-06 16:41:15Z yuppie $
"""

from zope.app import zapi

from Products.GenericSetup.interfaces import IBody
from Products.GenericSetup.utils import PropertyManagerHelpers
from Products.GenericSetup.utils import XMLAdapterBase

from Products.CMFCore.interfaces import ISiteRoot

_FILENAME = 'properties.xml'


class PropertiesXMLAdapter(XMLAdapterBase, PropertyManagerHelpers):

    """XML im- and exporter for properties.
    """

    __used_for__ = ISiteRoot

    _LOGGER_ID = 'properties'

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._doc.createElement('site')
        node.appendChild(self._extractProperties())

        self._logger.info('Site properties exported.')
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        if self.environ.shouldPurge():
            self._purgeProperties()

        self._initProperties(node)

        self._logger.info('Site properties imported.')


def importSiteProperties(context):
    """ Import site properties from an XML file.
    """
    site = context.getSite()
    logger = context.getLogger('properties')

    body = context.readDataFile(_FILENAME)
    if body is None:
        logger.info('Nothing to import.')
        return

    importer = zapi.queryMultiAdapter((site, context), IBody)
    if importer is None:
        logger.warning('Import adapter misssing.')
        return

    importer.body = body

def exportSiteProperties(context):
    """ Export site properties as an XML file.
    """
    site = context.getSite()
    logger = context.getLogger('properties')

    exporter = zapi.queryMultiAdapter((site, context), IBody)
    if exporter is None:
        logger.warning('Export adapter misssing.')
        return

    context.writeDataFile(_FILENAME, exporter.body, exporter.mime_type)
