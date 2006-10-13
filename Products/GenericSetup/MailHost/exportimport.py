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
"""MailHost export / import support.

$Id: exportimport.py 40878 2005-12-18 21:57:56Z yuppie $
"""

from Products.GenericSetup.utils import XMLAdapterBase

from Products.MailHost.interfaces import IMailHost


class MailHostXMLAdapter(XMLAdapterBase):

    """XML im- and exporter for MailHost.
    """

    __used_for__ = IMailHost

    _LOGGER_ID = 'mailhost'

    name = 'mailhost'

    def _exportNode(self):
        """Export the object as a DOM node.
        """
        node = self._getObjectNode('object')
        node.setAttribute('smtp_host', str(self.context.smtp_host))
        node.setAttribute('smtp_port', str(self.context.smtp_port))
        node.setAttribute('smtp_uid', self.context.smtp_uid)
        node.setAttribute('smtp_pwd', self.context.smtp_pwd)

        self._logger.info('Mailhost exported.')
        return node

    def _importNode(self, node):
        """Import the object from the DOM node.
        """
        self.context.smtp_host = str(node.getAttribute('smtp_host'))
        self.context.smtp_port = int(node.getAttribute('smtp_port'))
        self.context.smtp_uid = node.getAttribute('smtp_uid').encode('utf-8')
        self.context.smtp_pwd = node.getAttribute('smtp_pwd').encode('utf-8')

        self._logger.info('Mailhost imported.')
