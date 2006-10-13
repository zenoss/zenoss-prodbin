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
"""PythonScript export / import support.

$Id: exportimport.py 40314 2005-11-22 13:21:47Z yuppie $
"""

from Products.GenericSetup.utils import BodyAdapterBase

from interfaces import IPythonScript


class PythonScriptBodyAdapter(BodyAdapterBase):

    """Body im- and exporter for PythonScript.
    """

    __used_for__ = IPythonScript

    def _exportBody(self):
        """Export the object as a file body.
        """
        return self.context.read()

    def _importBody(self, body):
        """Import the object from the file body.
        """
        self.context.write(body)

    body = property(_exportBody, _importBody)

    mime_type = 'text/plain'

    suffix = '.py'
