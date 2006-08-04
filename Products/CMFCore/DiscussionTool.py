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
""" Basic portal discussion access tool.

$Id: DiscussionTool.py 37074 2005-06-20 17:19:21Z yuppie $
"""

from OFS.SimpleItem import SimpleItem
from Globals import InitializeClass, DTMLFile
from Acquisition import Implicit
from AccessControl import ClassSecurityInfo

from ActionProviderBase import ActionProviderBase
from permissions import AccessContentsInformation
from permissions import ManagePortal
from permissions import ReplyToItem
from permissions import View
from interfaces.Discussions import OldDiscussable as IOldDiscussable
from interfaces.portal_discussion \
        import oldstyle_portal_discussion as IOldstyleDiscussionTool
from utils import _dtmldir
from utils import getToolByName
from utils import UniqueObject


class OldDiscussable(Implicit):
    """
        Adapter for PortalContent to implement "old-style" discussions.
    """

    __implements__ = IOldDiscussable

    _isDiscussable = 1

    security = ClassSecurityInfo()
    

    def __init__( self, content ):
        self.content = content

    security.declareProtected(ReplyToItem, 'createReply')
    def createReply(self, title, text, REQUEST, RESPONSE):
        """
            Create a reply in the proper place
        """

        location, id = self.getReplyLocationAndID(REQUEST)
        location.addDiscussionItem(id, title, title, 'structured-text',
                                   text, self.content)

        RESPONSE.redirect( self.absolute_url() + '/view' )

    def getReplyLocationAndID(self, REQUEST):
        # It is not yet clear to me what the correct location for this hook is

        # Find the folder designated for replies, creating if missing
        membershiptool = getToolByName(self.content, 'portal_membership')
        home = membershiptool.getHomeFolder()
        if not hasattr(home, 'Correspondence'):
            home.manage_addPortalFolder('Correspondence')
        location = home.Correspondence
        location.manage_permission(View, ['Anonymous'], 1)
        location.manage_permission(AccessContentsInformation, ['Anonymous'], 1)

        # Find an unused id in location
        id = int(DateTime().timeTime())
        while hasattr(location, `id`):
            id = id + 1

        return location, `id`

    security.declareProtected(View, 'getReplyResults')
    def getReplyResults(self):
        """
            Return the ZCatalog results that represent this object's replies.

            Often, the actual objects are not needed.  This is less expensive
            than fetching the objects.
        """
        catalog = getToolByName(self.content, 'portal_catalog')
        return catalog.searchResults(in_reply_to=
                                      urllib.unquote('/'+self.absolute_url(1)))

    security.declareProtected(View, 'getReplies')
    def getReplies(self):
        """
            Return a sequence of the DiscussionResponse objects which are
            associated with this Discussable
        """
        catalog = getToolByName(self.content, 'portal_catalog')
        results = self.getReplyResults()
        rids    = map(lambda x: x.data_record_id_, results)
        objects = map(catalog.getobject, rids)
        return objects

    def quotedContents(self):
        """
            Return this object's contents in a form suitable for inclusion
            as a quote in a response.
        """

        return ""


class DiscussionTool (UniqueObject, SimpleItem, ActionProviderBase):

    __implements__ = (IOldstyleDiscussionTool,
                      ActionProviderBase.__implements__)

    id = 'portal_discussion'
    meta_type = 'Oldstyle CMF Discussion Tool'
    # This tool is used to find the discussion for a given content object.

    security = ClassSecurityInfo()

    manage_options = ( { 'label' : 'Overview', 'action' : 'manage_overview' }
                     , 
                     ) + SimpleItem.manage_options

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainDiscussionTool', _dtmldir )

    #
    #   'portal_discussion' interface methods
    #
    security.declarePublic('getDiscussionFor')
    def getDiscussionFor(self, content):
        '''Gets the PortalDiscussion object that applies to content.
        '''
        return OldDiscussable( content ).__of__( content )

    security.declarePublic('isDiscussionAllowedFor')
    def isDiscussionAllowedFor(self, content):
        '''
            Returns a boolean indicating whether a discussion is
            allowed for the specified content.
        '''
        if hasattr( content, 'allow_discussion' ):
            return content.allow_discussion
        typeInfo = getToolByName(self, 'portal_types').getTypeInfo( content )
        if typeInfo:
            return typeInfo.allowDiscussion()
        return 0

    security.declarePrivate('listActions')
    def listActions(self, info=None, object=None):
        # Return actions for reply and show replies
        if object is not None or info is None:
            info = self._getOAI(object)
        content = info.object
        if content is None or not self.isDiscussionAllowedFor(content):
            return ()

        discussion = self.getDiscussionFor(content)
        if discussion.aq_base == content.aq_base:
            discussion_url = info.object_url
        else:
            discussion_url = discussion.absolute_url()

        actions = (
            {'name': 'Reply',
             'url': discussion_url + '/discussion_reply_form',
             'permissions': [ReplyToItem],
             'category': 'object'
             },
            )

        return actions

InitializeClass(DiscussionTool)
