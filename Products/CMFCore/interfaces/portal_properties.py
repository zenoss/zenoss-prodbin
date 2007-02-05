##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Properties tool interface.

$Id: portal_properties.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_properties(Interface):
    """ CMF Properties Tool interface.

    This interface provides access to "portal-wide" properties.
    """
    id = Attribute('id', 'Must be set to "portal_properties"')

    def editProperties(props):
        """ Change portal settings.

        Permission -- Manage portal
        """

    def title():
        """ Get portal title.

        Returns -- String
        """

    def smtp_server():
        """ Get local SMTP server.

        Returns -- String
        """
