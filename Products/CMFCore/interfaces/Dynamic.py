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
""" Dynamic type interface.

$Id: Dynamic.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Interface


class DynamicType(Interface):
    """ General interface for dynamic items.
    """

    def getPortalTypeName():
        """ Get the portal type name that can be passed to portal_types.

        If the object is uninitialized, returns None.

        Permission -- Always available
        """

    def getTypeInfo():
        """ Get the TypeInformation object specified by the portal type.

        A shortcut to 'getTypeInfo' of portal_types.

        Permission -- Always available
        """

    def getActionInfo(action_chain, check_visibility=0, check_condition=0):
        """ Get an Action info mapping specified by a chain of actions.

        A shortcut to 'getActionInfo' of the related TypeInformation object.

        Permission -- Always available
        """

    def getIcon(relative_to_portal=0):
        """ Get the path to an object's icon.

        This method is used in the folder_contents view to generate an
        appropriate icon for the items found in the folder.

        If the content item does not define an attribute named "icon"
        this method will return the path "/misc_/dtmldoc.gif", which is
        the icon used for DTML Documents.

        If 'relative_to_portal' is true, return only the portion of
        the icon's URL which finds it "within" the portal;  otherwise,
        return it as an absolute URL.

        Permission -- Always available
        """
