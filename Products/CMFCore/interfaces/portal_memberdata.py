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
""" Memberdata storage tool interface.

$Id: portal_memberdata.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_memberdata(Interface):
    '''A helper for portal_membership that transparently adds
    member data to user objects.
    '''
    id = Attribute('id', 'Must be set to "portal_memberdata"')

    ## wrapUser__roles__ = ()  # Private.
    def wrapUser(u):
        '''
        If possible, returns the Member object that corresponds
        to the given User object.
        '''
    ## getMemberDataContents__roles__ = ()  # Private.
    def getMemberDataContents():
        '''
        Returns a list containing a dictionary with information
        about the _members BTree contents: member_count is the
        total number of member instances stored in the memberdata-
        tool while orphan_count is the number of member instances
        that for one reason or another are no longer in the
        underlying acl_users user folder.
        The result is designed to be iterated over in a dtml-in
        '''

    def pruneMemberDataContents():
        """ Delete member data of all members not listet in acl_users.

        Compare the user IDs stored in the member data tool with the list in
        the actual underlying acl_users and delete anything not in acl_users.

        Permission -- Python only
        """

    def searchMemberData(search_param, search_term, attributes=()):
        """ Search members.

        Returns a sequence of dictionaries containing data for members
        that match the query as expressed by search_param and search_term.
        The contents of each member data mapping can be influenced by
        passing in a sequence of desired attributes, by default the only
        data returned is the username and the email address.

        Permission -- Python only

        Returns -- Sequence of dictionaries
        """

    def registerMemberData(m, id):
        """ Add the given member data to the _members btree.

        This is done as late as possible to avoid side effect transactions and
        to reduce the necessary number of entries.

        Permission -- Python only
        """

    def deleteMemberData(member_id):
        """ Delete member data of specified member.

        Permission -- Python only

        Returns -- Boolean value
        """


class MemberData(Interface):
    """ MemberData interface.
    """

    def setProperties(properties=None, **kw):
        """ Allows the authenticated member to set his/her own properties.

        Permission -- Set own properties
        """
