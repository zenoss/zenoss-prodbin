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
""" Membership tool interface.

$Id: portal_membership.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_membership(Interface):
    """ Deals with the details of how and where to store and retrieve
    members and their member folders.
    """
    id = Attribute('id', 'Must be set to "portal_membership"')

    def setPassword(password, domains=None):
        """ Allows the authenticated member to set his/her own password.

        Permission -- Set own password
        """

    def getAuthenticatedMember():
        """
        Returns the currently authenticated member object
        or the Anonymous User.

        Permission -- Always available
        """

    def isAnonymousUser():
        """
        Returns 1 if the user is not logged in.

        Permission -- Always available
        """

    def checkPermission(permissionName, object, subobjectName=None):
        """
        Checks whether the current user has the given permission on
        the given object or subobject.

        Permission -- Always available
        """

    def credentialsChanged(password):
        """
        Notifies the authentication mechanism that this user has changed
        passwords.  This can be used to update the authentication cookie.
        Note that this call should *not* cause any change at all to user
        databases.

        Permission -- Always available
        """

    def getMembersFolder():
        """ Get the members folder object.

        If no members folder is set or the set folder id doesn't exist, None
        is returned.

        Permission -- Always available

        Returns -- Members folder object or None
        """

    def getHomeFolder(id=None, verifyPermission=0):
        """Returns a member's home folder object or None.
        Set verifyPermission to 1 to return None when the user
        doesn't have the View permission on the folder.

        Permission -- Always available
        """

    def getHomeUrl(id=None, verifyPermission=0):
        """Returns the URL to a member's home folder or None.
        Set verifyPermission to 1 to return None when the user
        doesn't have the View permission on the folder.

        Permission -- Always available
        """

    def getMemberById(id):
        """
        Returns the given member.

        Permission -- Manage users
        """

    def listMemberIds():
        """ Lists the ids of all members.

        This may eventually be replaced with a set of methods for querying
        pieces of the list rather than the entire list at once.

        Permission -- Manage users
        """

    def listMembers():
        """ Gets the list of all members.

        Permission -- Manage users
        """

    def getCandidateLocalRoles(obj):
        """ What local roles can I assign?

        Permission -- Always available

        Returns -- Tuple of roles
        """

    def setLocalRoles(obj, member_ids, member_role, reindex=1):
        """ Add local roles on an item.

        Permission -- Always available
        """

    def deleteLocalRoles(obj, member_ids, reindex=1, recursive=0):
        """ Delete local roles of specified members.

        Permission -- Always available
        """

    def addMember(id, password, roles, domains):
        """ Adds a new member to the user folder.

        Security checks will have already been performed. Called by
        portal_registration.

        Permission -- Python only
        """

    def deleteMembers(member_ids, delete_memberareas=1, delete_localroles=1):
        """ Delete members specified by member_ids.

        Delete members in acl_users and member data in portal_memberdata.
        If delete_memberareas is true, delete members' home folders including
        all content items. If delete_localroles is true, recursively delete
        members' local roles, starting from the portal root.

        Permission -- Manage users

        Returns -- Tuple listing member_ids of deleted members
        """

    def getPortalRoles():
        """
        Return all local roles defined by the portal itself,
        which means roles that are useful and understood
        by the portal object

        Permission -- Manage portal
        """

    def setRoleMapping(portal_role, userfolder_role):
        """
        set the mapping of roles between roles understood by
        the portal and roles coming from outside user sources

        Permission -- Manage portal
        """

    def getMappedRole(portal_role):
        """
        returns a role name if the portal role is mapped to
        something else or an empty string if it is not

        Permission -- Manage portal
        """

    def getMemberareaCreationFlag():
        """
        Returns the flag indicating whether the membership tool
        will create a member area if an authenticated user from
        an underlying user folder logs in first without going
        through the join process

        Permission -- Manage portal
        """

    def setMemberareaCreationFlag():
        """
        sets the flag indicating whether the membership tool
        will create a member area if an authenticated user from
        an underlying user folder logs in first without going
        through the join process

        Permission -- Manage portal
        """

    def createMemberArea(member_id=''):
        """ Create a member area for 'member_id' or authenticated user.

        Permission -- Always available

        Returns -- created member folder object or None
        """

    def createMemberarea(member_id=''):
        """ Deprecated alias of createMemberArea.
        """

    def deleteMemberArea(member_id):
        """ Delete member area of member specified by member_id.

        Permission -- Manage users

        Returns -- Boolean value
        """
