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
""" Folderish type interface.

$Id: Folderish.py 40138 2005-11-15 17:47:37Z jens $
"""

from Interface import Interface


class Folderish(Interface):
    """ General interface for "folderish" items.
    """

    def contentItems(spec=None, filter=None):
        """ List contentish and folderish sub-objects and their IDs.

        Provide a filtered view onto 'objectItems', allowing only
        PortalFolders and PortalContent-derivatives to show through.

        The 'spec' argument is deprecated and will be removed in CMF 2.0.

        Permission -- Always available (not publishable)

        Returns -- List of (object ID, object) tuples
        """

    def contentIds(spec=None, filter=None):
        """ List IDs of contentish and folderish sub-objects.

        Provide a filtered view onto 'objectIds', allowing only PortalFolders
        and PortalContent-derivatives to show through.

        The 'spec' argument is deprecated and will be removed in CMF 2.0.

        Permission -- Always available (not publishable)

        Returns -- List of object IDs
        """

    def contentValues(spec=None, filter=None):
        """ List contentish and folderish sub-objects.

        Provide a filtered view onto 'objectValues', allowing only
        PortalFolders and PortalContent-derivatives to show through.

        The 'spec' argument is deprecated and will be removed in CMF 2.0.

        Permission -- Always available (not publishable)

        Returns -- List of objects
        """

    def listFolderContents(spec=None, contentFilter=None):
        """ List viewable contentish and folderish sub-objects.

        Hook around 'contentValues' to let 'folder_contents' be protected.
        Duplicating skip_unauthorized behavior of dtml-in.

        The 'spec' argument is deprecated and will be removed in CMF 2.0.

        Permission -- List folder contents

        Returns -- List of objects
        """
