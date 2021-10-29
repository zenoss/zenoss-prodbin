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

    def createGroups(self, groups):
        infoGroups = []
        for groupName in groups:
            self._root.manage_addGroup(groupName)
            group = self._root.getGroupSettings(groupName)
            infoGroups.append(group)
        return infoGroups

    def removeGroups(self, groups):
        ids = groups
        if isinstance(ids, basestring):
            groups = [ids]
        return self._root.manage_deleteGroups(groups)

    def listGroupsForEachUser(self, users=()):
        usergroups = self._root.manage_listGroupNamesForUser(userids=users)
        return usergroups

    def listGroupMembers(self, groups=()):
        groupusers = self._root.manage_listGroupMembers(groupids=groups)
        return groupusers

    def addUsersToGroups(self, users, groups):

        # Create any new groups and add the user to the listed groups
        curGrpNames = self._dmd.ZenUsers.getAllGroupSettingsNames()
        for group in groups:
            if group not in curGrpNames:
                self.createGroups([group])

        # can pass string or list of strings
        return self._root.manage_addUsersToGroups(users, groups)

    def removeUsersFromGroups(self, users, groups):
        # can pass string or list of strings
        return self._root.manage_removeUsersFromGroups(users, groups)

    def assignZenUserRoleToUsers(self, users):
        infoUsers = []
        for user in users:
            roles = self._root.getUserRoles(user)
            if "ZenUser" not in roles:
                roles.append("ZenUser")
                iusr = self._root.manage_changeUser(user, roles=roles)
                infoUsers.append(iusr)
        return infoUsers

    def removeZenUserRoleFromUsers(self, users):
        infoUsers = []
        for user in users:
            roles = self._root.getUserRoles(user)
            if "ZenUser" in roles:
                roles.remove("ZenUser")
                iusr = self._root.manage_changeUser(user, roles=roles)
                infoUsers.append(iusr)
        return infoUsers

    def assignAdminRolesToUsers(self, users):
        return self._root.manage_assignAdminRolesToUsers(users)

    def removeAdminRolesFromUsers(self, users):
        return self._root.manage_removeAdminRolesFromUsers(users)
