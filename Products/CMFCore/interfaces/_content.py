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
""" CMFCore content interfaces.

$Id: _content.py 38636 2005-09-25 22:42:33Z tseaver $
"""

from zope.interface import Interface
from zope.interface import Attribute


#
#   Contentish interface
#
class IContentish(Interface):

    """ General interface for "contentish" items.

    o These methods need to be implemented by any class that wants to be a
      first-class citizen in the CMF world.

    o CMFCore.PortalContent implements this interface.
    """

    def SearchableText():
        """ Return a string containing textual information about the content.

        o This string may be the content of a file, or may be synthesized
          by concatenating the string attributes of the instance.

        o Permissions:  View
        """


#
#   Discussable interfaces
#
class IDiscussable(Interface):

    """ Interface for things which can have responses.
    """

    def createReply(title, text, Creator=None):
        """ Create a reply in the proper place.

        o Returns: HTML (directly or via redirect) # XXX

        o Permission: Reply to item
        """

    def getReplies():
        """ Return a sequence of IDiscussionResponse objects which are
            replies to this IDiscussable

        o Permission: View
        """

    def quotedContents():
        """ Return this object's contents in a form suitable for inclusion
            as a quote in a response.

        o The default implementation returns an empty string.  It might be
           overridden to return a '>' quoted version of the item.

        o Permission: Reply to item
        """

    def _getReplyResults():
        """ Return the ZCatalog results that represent this object's replies.

        o XXX: Huh?

        o Often, the actual objects are not needed.  This is less expensive
          than fetching the objects.

        o Permission: View
        """


class IOldstyleDiscussable(Interface):

    """ Oldstyle discussable interface.
    """

    def createReply(title, text, REQUEST, RESPONSE):
        """ Create a reply in the proper place.

        o Returns: HTML (directly or via redirect) # XXX

        o Permission: Reply to item
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


class IDiscussionResponse(Interface):

    """ Interface for objects which are replies to IDiscussable objects.
    """

    def inReplyTo(REQUEST=None):
        """ Return the IDiscussable object to which this item is a reply.

        o Permission: None assigned
        """

    def setReplyTo(reply_to):
        """ Make this object a response to the passed object.

        o 'reply_to' is an IDiscussable, or a path (as a string) to one.

        o Raise ValueError if 'reply_to' is not an IDiscussable (or doesn't
          resolve to one as a path).

        o XXX This does not seem like the right exception.

        o Permission: None assigned
        """

    def parentsInThread(size=0):
        """ Return a sequence of IDiscussables which are this object's parents,
            from the point of view of the threaded discussion.

        o Parents are ordered oldest to newest.

        o If 'size' is not zero, only the closest 'size' parents will be
          returned.
        """


#
#   DublinCore interfaces
#
class IDublinCore(Interface):

    """ Dublin Core metadata elements supported by CMF and their semantics.
    """

    def Title():
        """ Return a single string, the DCMI Title element (resource name).

        o Permission:  View
        """

    def listCreators():
        """ Return a sequence of DCMI Creator elements (resource authors).

        o Depending on the implementation, this returns the full name(s) of the
          author(s) of the content object or their ids.

        o Permission:  View
        """

    def Creator():
        """ Return the first DCMI Creator element, or an empty string.

        o Permission:  View
        """

    def Subject():
        """ Return a sequence of DCMI Subject elements (resource keywords).

        o Result is zero or more keywords associated with the content object.

        o Permission:  View
        """

    def Description():
        """ Reuturn the DCMI Description element (resource summary).

        o Result is a natural language description of this object.

        o Permission:  View
        """

    def Publisher():
        """ Return the DCMI Publisher element (resource publisher).

        o Result is the full formal name of the entity or person responsible
          for publishing the resource.

        o Permission:  View
        """

    def listContributors():
        """ Return a sequence of DCMI Contributor elements (resource
            collaborators).

        o Return zero or more collaborators (beyond thos returned by
          'listCreators').

        o Permission:  View
        """

    def Contributors():
        """ Deprecated alias for 'listContributors'.

        o 'initial caps' names are reserved for strings.
        """

    def Date():
        """ Return the DCMI Date element (default resource date).

        o Result is a string, formatted 'YYYY-MM-DD H24:MN:SS TZ'.

        o Permission:  View
        """

    def CreationDate():
        """ Return the DCMI Date element (date resource created).

        o Result is a string, formatted 'YYYY-MM-DD H24:MN:SS TZ'.

        o Permission:  View
        """

    def EffectiveDate():
        """ Return the DCMI Date element (date resource becomes effective).

        o Result is a string, formatted 'YYYY-MM-DD H24:MN:SS TZ', or
          None.

        o Permission:  View
        """

    def ExpirationDate():
        """ Return the DCMI Date element (date resource expires).

        o Result is a string, formatted 'YYYY-MM-DD H24:MN:SS TZ', or
          None.

        o Permission:  View
        """

    def ModificationDate():
        """ DCMI Date element - date resource last modified.

        o Result is a string, formatted 'YYYY-MM-DD H24:MN:SS TZ'.

        o Permission:  View
        """

    def Type():
        """ Return the DCMI Type element (resource type).

        o Result a human-readable type name for the resource (typically
          the Title of its type info object).

        o Permission:  View
        """

    def Format():
        """ Return the DCMI Format element (resource format).

        o Result is the resource's MIME type (e.g. 'text/html',
          'image/png', etc.).

        o Permission:  View
        """

    def Identifier():
        """ Return the DCMI Identifier element (resource ID).

        o Result is a unique ID (a URL) for the resource.

        o Permission:  View
        """

    def Language():
        """ DCMI Language element (resource language).

        o Result it the RFC language code (e.g. 'en-US', 'pt-BR') for the
          resource.

        o Permission:  View
        """

    def Rights():
        """ Reutrn the DCMI Rights element (resource copyright).

        o Return a string describing the intellectual property status, if
          any, of the resource.

        o Permission:  View
        """


class ICatalogableDublinCore(Interface):

    """ Provide Zope-internal date attributes for cataloging purposes.
    """

    def created():
        """ Return the DateTime form of CreationDate.

        o Permission:  View
        """

    def effective():
        """ Return the DateTime form of EffectiveDate.

        o Permission:  View
        """

    def expires():
        """ Return the DateTime form of ExpirationDate.

        o Permission:  View
        """

    def modified():
        """ Return the DateTime form of ModificationDate

        o Permission:  View
        """


class IMutableDublinCore(Interface):

    """ Update interface for mutable metadata.
    """

    def setTitle(title):
        """ Set DCMI Title element - resource name.

        o Permission:  Modify portal content
        """

    def setCreators(creators):
        """ Set DCMI Creator elements - resource authors.

        o Permission:  Modify portal content
        """

    def setSubject(subject):
        """ Set DCMI Subject element - resource keywords.

        o Permission:  Modify portal content
        """

    def setDescription(description):
        """ Set DCMI Description element - resource summary.

        o Permission:  Modify portal content
        """

    def setContributors(contributors):
        """ Set DCMI Contributor elements - resource collaborators.

        o Permission:  Modify portal content
        """

    def setEffectiveDate(effective_date):
        """ Set DCMI Date element - date resource becomes effective.

        o Permission:  Modify portal content
        """

    def setExpirationDate(expiration_date):
        """ Set DCMI Date element - date resource expires.

        o Permission:  Modify portal content
        """

    def setFormat(format):
        """ Set DCMI Format element - resource format.

        o Permission:  Modify portal content
        """

    def setLanguage(language):
        """ Set DCMI Language element - resource language.

        o Permission:  Modify portal content
        """

    def setRights(rights):
        """ Set DCMI Rights element - resource copyright.

        o Permission:  Modify portal content
        """


#
#   DynamicType interfaces
#
class IDynamicType(Interface):

    """ General interface for dynamic items.
    """

    def getPortalTypeName():
        """ Return the name of the type information for this object.

        o If the object is uninitialized, return None.

        o Permission:  Public
        """

    def getTypeInfo():
        """ Return the ITypeInformation object for this object.

        o A shortcut to 'getTypeInfo' of portal_types.

        o Permission:  Public
        """

    def getActionInfo(action_chain, check_visibility=0, check_condition=0):
        """ Get an Action info mapping specified by a chain of actions.

        o A shortcut to 'getActionInfo' of the related ITypeInformation
          object.

        o Permission:  Public
        """

    def getIcon(relative_to_portal=False):
        """ Get the path to an object's icon.

        o This method is used in the 'folder_contents' view to generate an
          appropriate icon for the items found in the folder.

        o If the content item does not define an attribute named "icon"
          return a "default" icon path (e.g., '/misc_/dtmldoc.gif', which is
          the icon used for DTML Documents).

        o If 'relative_to_portal' is True, return only the portion of
          the icon's URL which finds it "within" the portal;  otherwise,
          return it as an absolute URL.

        o Permission:  Public
        """


#
#   Folderish interface
#
class IFolderish(Interface):

    """ General interface for "folderish" content items.
    """

    def contentItems(filter=None):
        """ Return a sequence of (object ID, object) tuples for
            IContentish and IFolderish sub-objects.

        o Provide a filtered view onto 'objectItems', allowing only
          "content space" objects to show through.

        o Permission:  Public (not publishable)
        """

    def contentIds(filter=None):
        """ Return a sequence of IDs of IContentish and IFolderish sub-objects.

        o Provide a filtered view onto 'objectIds', allowing only
          "content space" objects to show through.

        o Permission:  Public (not publishable)

        Returns -- List of object IDs
        """

    def contentValues(filter=None):
        """ Return a sequence of IContentish and IFolderish sub-objects.

        o Provide a filtered view onto 'objectValues', allowing only
          "content space" objects to show through.

        o Permission:  Public (not publishable)

        Returns -- List of objects
        """

    def listFolderContents(contentFilter=None):
        """ Return a sequence of IContentish and IFolderish sub-objects,
            filtered by the current user's possession of the View permission.

        o Hook around 'contentValues' to let 'folder_contents' be protected.

        o Duplicates 'skip_unauthorized' behavior of 'dtml-in'.

        o Permission -- List folder contents
        """

class ISiteRoot(IFolderish):
    """ Marker interface for the object which serves as the root of a site.
    """

#
#   IOpaqueItems interfaces
#
class ICallableOpaqueItem(Interface):

    """ Interface for callable opaque items.

    o Opaque items are subelements that are contained using something that
      is not an ObjectManager.

    o On add, copy, move and delete operations, a marked opaque items
      'manage_afterAdd', 'manage_afterClone' and 'manage_beforeDelete'
      hooks get called if available. Unavailable hooks do not throw
      exceptions.
    """

    def __init__(obj, id):
        """Return the opaque item and assign it to 'obj' as attr with 'id'.
        """

    def __call__():
        """Return the opaque items value.
        """

    def getId():
        """Return the id of the opaque item.
        """


class ICallableOpaqueItemEvents(Interface):

    """CMF specific events upon copying, renaming and deletion.
    """

    def manage_afterClone(item):
        """After clone event hook.
        """

    def manage_beforeDelete(item, container):
        """Before delete event hook.
        """

    def manage_afterAdd(item, container):
        """After add event hook.
        """


#
#   Syndicatable interface
#
class ISyndicatable(Interface):

    """ Filter content for syndication.
    """

    def synContentValues():
        """ Return a list of IDublinCore objects to be syndicated.

        o For example, 'IFolderish' containers might returns a list of
          recently-created or modified subobjects.

        o Topics might return a sequence of objects from a catalog query.
        """
