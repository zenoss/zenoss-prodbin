##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" URL tool interface.

$Id: portal_url.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_url(Interface):
    """ CMF URL Tool interface.

    This interface provides a common mechanism for finding the 'root'
    object of a CMFSite, and for computing paths to objects relative to
    that root.
    """
    id = Attribute('id', 'Must be set to "portal_url"')

    def __call__(relative=0, *args, **kw):
        """ Get by default the absolute URL of the portal.

        Permission -- Always available

        Returns -- Slash-separated string
        """

    def getPortalObject():
        """ Get the portal object itself.

        Permission -- Always available

        Returns -- CMFSite object
        """

    def getRelativeContentPath(content):
        """ Get the path for an object, relative to the portal root.

        Permission -- Always available

        Returns -- Tuple of IDs
        """

    def getRelativeContentURL(content):
        """ Get the URL for an object, relative to the portal root.

        This is helpful for virtual hosting situations.
        Same method as 'getRelativeURL()'

        Permission -- Always available

        Returns -- Slash-separated string
        """

    def getRelativeUrl(content):
        """ Get the URL for an object, relative to the portal root.

        This is helpful for virtual hosting situations.
        Same method as 'getRelativeContentURL()'

        Permission -- Always available

        Returns -- Slash-separated string
        """

    def getPortalPath():
        """ Get the portal object's URL without the server URL component.

        Permission -- Always available

        Returns -- Slash-separated string
        """
