##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
log = logging.getLogger('zen.userfacade')

from zope.interface import implements
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IUserFacade, IInfo
from Products.Zuul.tree import SearchResults


class UserFacade(ZuulFacade):
    implements(IUserFacade)

    @property
    def _root(self):
        return self._dmd.ZenUsers

    def setAdminPassword(self, newPassword):
        userManager = self._dmd.getPhysicalRoot().acl_users.userManager
        userManager.updateUserPassword('admin', newPassword)

    def removeUsers(self, userIds):
        ids = userIds
        if isinstance(ids, basestring):
            userIds = [ids]
        return self._root.manage_deleteUsers(userIds)

    def getUsers(self, start=0, limit=50, sort='name', dir='ASC', name=None):
        users = map(IInfo, self._dmd.ZenUsers.getAllUserSettings())
        sortedUsers = sorted(users, key=lambda u: getattr(u, sort))
        if dir == "DESC":
            sortedUsers.reverse()
        total = len(sortedUsers)
        return SearchResults(iter(sortedUsers[start:limit]), total, total, areBrains=False)

    def addUser(self, id, password, email, roles):
        propertiedUser = self._root.manage_addUser(id, password, roles)
        user = self._root.getUserSettings(propertiedUser.getId())
        user.email = email
        return IInfo(user)

    def getGroups(self, start=0, limit=50, sort='id', dir='ASC', name=None):
        groups = map(IInfo, self._dmd.ZenUsers.getAllGroupSettings())
        sortedGroups = sorted(groups, key=lambda u: getattr(u, sort))
        if dir == "DESC":
            sortedGroups.reverse()
        total = len(sortedGroups)
        return SearchResults(iter(sortedGroups[start:limit]), total, total, areBrains=False)

    def createGroup(self, groupName):
        self._root.manage_addGroup(groupName)
        group = self._root.getGroupSettings(groupName)
        return IInfo(group)

    def removeGroups(self, groupIds):
        ids = groupIds
        if isinstance(ids, basestring):
            groupIds = [ids]
        return self._root.manage_deleteGroups(groupIds)

    def addUsersToGroups(self, userIds, groupIds):
        # can pass string or list of strings
        return self._root.manage_addUsersToGroups(userIds, groupIds)

    def removeUsersFromGroups(self, userIds, groupIds):
        # can pass string or list of strings
        return self._root.manage_removeUsersFromGroups(userIds, groupIds)

    def assignAdminRolesToUsers(self, userIds):
        return self._root.manage_assignAdminRolesToUsers(userIds)

    def removeAdminRolesFromUsers(self, userIds):
        return self._root.manage_removeAdminRolesFromUsers(userIds)
