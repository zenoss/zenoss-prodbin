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
""" Contentish type interface.

$Id: Contentish.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Interface


class Contentish(Interface):
    """
    General interface for "contentish" items.

    These methods need to be implemented by any class that wants to be a
    first-class citizen in the Portal Content world.

    PortalContent implements this interface.
    """

    def SearchableText():
        """
        SearchableText is called to provide the Catalog with textual
        information about your object. It is a string usually generated
        by concatenating the string attributes of your content class. This
        string can then be used by the catalog to index your document and
        make it findable through the catalog.
        """
