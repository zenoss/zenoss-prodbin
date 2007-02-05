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
""" Discussable interface.

$Id: Discussions.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Interface


class Discussable(Interface):
    """ Discussable is the interface for things which can have responses.
    """

    def createReply(title, text, Creator=None):
        """
        Create a reply in the proper place.

        Permission: Reply to item
        Returns: HTML (directly or via redirect)
        """

    def getReplies():
        """
        Return a sequence of the DiscussionResponse objects which are
        associated with this Discussable

        Permissions: View
        Returns: sequence of DiscussionResponses
        """

    def quotedContents():
        """
        Return this object's contents in a form suitable for inclusion
        as a quote in a response.  The default implementation returns
        an empty string.  It might be overridden to return a '>' quoted
        version of the item.
        """

    def _getReplyResults():
        """
        Return the ZCatalog results that represent this object's replies.

        Often, the actual objects are not needed.  This is less expensive
        than fetching the objects.

        Permissions: View
        Returns: sequence of ZCatalog results representing DiscussionResponses
        """


class OldDiscussable(Interface):
    """ Oldstyle discussable interface.
    """

    def createReply(title, text, REQUEST, RESPONSE):
        """
        Create a reply in the proper place.

        Permission: Reply to item
        Returns: HTML (directly or via redirect)
        """

    def getReplyLocationAndID(REQUEST):
        """
        This method determines where a user's reply should be stored, and
        what it's ID should be.

        You don't really want to force users to have to select a
        unique ID each time they want to reply to something.  The
        present implementation selects a folder in the Member's home
        folder called 'Correspondence' (creating it if it is missing)
        and finds a free ID in that folder.

        createReply should use this method to determine what the reply
        it creates should be called, and where it should be placed.

        This method (and createReply, I expect) do not really belong in
        this interface.  There should be a DiscussionManager singleton
        (probably the portal object itself) which handles this.

        Permissions: None assigned
        Returns: 2-tuple, containing the container object, and a string ID.
        """

    def getReplyResults():
        """
        Return the ZCatalog results that represent this object's replies.

        Often, the actual objects are not needed.  This is less expensive
        than fetching the objects.

        Permissions: View
        Returns: sequence of ZCatalog results representing DiscussionResponses
        """

    def getReplies():
        """
        Return a sequence of the DiscussionResponse objects which are
        associated with this Discussable

        Permissions: View
        Returns: sequence of DiscussionResponses
        """

    def quotedContents():
        """
        Return this object's contents in a form suitable for inclusion
        as a quote in a response.  The default implementation returns
        an empty string.  It might be overridden to return a '>' quoted
        version of the item.
        """


class DiscussionResponse(Interface):
    """ This interface describes the behaviour of a Discussion Response.
    """

    def inReplyTo(REQUEST=None):
        """
        Return the Discussable object which this item is associated with

        Permissions: None assigned
        Returns: a Discussable object
        """

    def setReplyTo(reply_to):
        """
        Make this object a response to the passed object.  (Will also
        accept a path in the form of a string.)  If reply_to does not
        support or accept replies, a ValueError will be raised.  (This
        does not seem like the right exception.)

        Permissions: None assigned
        Returns: None
        """

    def parentsInThread(size=0):
        """
        Return the list of object which are this object's parents, from the
        point of view of the threaded discussion.  Parents are ordered
        oldest to newest.

        If 'size' is not zero, only the closest 'size' parents will be
        returned.
        """
