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
""" Type registration tool interface.

$Id: portal_types.py 40138 2005-11-15 17:47:37Z jens $
"""

from Interface import Attribute
from Interface import Interface


class ContentTypeInformation(Interface):
    """
        Registry entry interface.
    """
    def Metatype():
        """
            Return the Zope 'meta_type' for this content object.

        o Deprecated (not all objects of a given type may even share
          the same meta_type).
        """

    def Title():
        """
            Return the "human readable" type name (note that it
            may not map exactly to the 'meta_type', e.g., for
            l10n/i18n or where a single content class is being
            used twice, under different names.
        """

    def Description():
        """
            Textual description of the class of objects (intended
            for display in a "constructor list").
        """

    def isConstructionAllowed(container):
        """
        Does the current user have the permission required in
        order to construct an instance?
        """

    def allowType(contentType):
        """
            Can objects of 'contentType' be added to containers whose
            type object we are?
        """

    def constructInstance(container, id):
        """
            Build a "bare" instance of the appropriate type in
            'container', using 'id' as its id.  Return the instance,
            seated in the container.
        """

    def allowDiscussion():
        """
            Can this type of object support discussion?
        """

    def getActionById(id):
        """ Get method ID by action ID.

        This method is deprecated and will be removed in CMF 2.0. Please use
        getActionInfo()['url'] if you need an URL or queryMethodID() if you
        need a method ID.
        """

    def getIcon():
        """
            Returns the portal-relative icon for this type.
        """

    def getMethodAliases():
        """ Get method aliases dict.

        Permission -- Manage portal

        Returns -- Dictionary
        """

    def setMethodAliases(aliases):
        """ Set method aliases dict.

        Permission -- Manage portal

        Returns -- Boolean value
        """

    def queryMethodID(alias, default=None, context=None):
        """ Query method ID by alias.
        
        context points to the object that calls queryMethodID. It may be used to
        return dynamic values based on the caller.

        Permission -- Always available

        Returns -- Method ID or default value
        """


class portal_types(Interface):
    """
        Provides a configurable registry of portal content types.
    """
    id = Attribute('id', 'Must be set to "portal_types"')

    # getType__roles__ = None  # Public
    def getTypeInfo(contentType):
        """
            Return an instance which implements the
            ContentTypeInformation interface, corresponding to
            the specified 'contentType'.  If contentType is actually
            an object, rather than a string, attempt to look up
            the appropriate type info using its portal_type.
        """

    # listTypeInfo__roles__ = None  # Public
    def listTypeInfo(container=None):
        """
            Return a sequence of instances which implement the
            ContentTypeInformation interface, one for each content
            type regisetered in the portal.  If the container
            is specified, the list will be filtered according to
            the user's permissions.
        """

    def listContentTypes(container=None, by_metatype=0):
        """
            Return list of content types, or the equivalent
            metatypes;  if 'container' is passed, then filter
            the list to include only types which are addable in
            'container'.
        """

    def constructContent(contentType, container, id, RESPONSE=None
                        , *args, **kw):
        """
            Build an instance of the appropriate content class in
            'container', using 'id'.  If RESPONSE is provided, redirect
            to the new object's "initial view", otherwise return the
            new object's Id string.
        """
