##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for Users
"""

import logging
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products import Zuul
from Products.ZenMessaging.audit import audit

log = logging.getLogger('zen.UserRouter')


class UsersRouter(DirectRouter):
    """
    A JSON/ExtDirect interface to operations on Users
    """

    def __init__(self, context, request):
        self.facade = Zuul.getFacade('user', context)
        self.context = context
        self.request = request
        super(UsersRouter, self).__init__(context, request)

    def _getFacade(self):
        return self.facade

    @require('Manage DMD')
    def setAdminPassword(self, newPassword):
        audit('UI.Users.UpdateAdminPassword')
        self.facade.setAdminPassword(newPassword)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteUsers(self, users):
        """
        Removes all the users with the given user ids. Will continue
        upon removing users if an invalid id is specified.
        @type  users: List of Strings
        @param users: (optional) list of user ids to remove.
        """
        facade = self._getFacade()
        facade.removeUsers(users)
        audit('UI.Users.RemoveUsers', userIds=users)
        return DirectResponse.succeed()

    def getUsers(self, keys=None, start=0, limit=50, page=0,
                    sort='name', dir='ASC', name=None):
        """
        Retrieves a list of users. This method supports pagination.
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  name: string
        @param name: (optional) filter to be applied to users returned (default: None)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: (list) Dictionaries of user properties
             - totalCount: (integer) Number of devices returned
        """
        facade = self._getFacade()
        users = facade.getUsers(start=start, limit=limit, sort=sort,
                                dir=dir, name=name)
        total = users.total
        data = Zuul.marshal(users, keys)
        return DirectResponse.succeed(data=data, totalCount=total)

    @require('Manage DMD')
    def addUser(self, name, password, email, groups=(), roles=()):
        """
        Adds a new user to the system.
        @type  name: string
        @param name: The unique identifier of the user, same as their login
        @type  password: string
        @param password: the password of the new user
        @type  groups: list of strings
        @param groups: (optional) groups to be applied to the new user
        @type  roles: list of strings
        @param roles: (optional) roles to be applied to the new user
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: properties of the new users
        """
        facade = self._getFacade()
        newUser = facade.addUser(name, password, email, groups, roles)
        audit('UI.Users.Add', name, email=email, roles=roles)
        return DirectResponse.succeed(data=Zuul.marshal(newUser))

    @require('Manage DMD')
    def getGroups(self, keys=None, start=0, limit=50, page=0, sort='name', dir='ASC', name=None):
        """
        Retrieves a list of groups. This method supports pagination.
        @type  start: integer
        @param start: (optional) Offset to return the results from; used in
                      pagination (default: 0)
        @type  name: string
        @param name: (optional) filter to be applied to groups returned (default: None)
        @type  limit: integer
        @param limit: (optional) Number of items to return; used in pagination
                      (default: 50)
        @type  sort: string
        @param sort: (optional) Key on which to sort the return results (default:
                     'name')
        @type  dir: string
        @param dir: (optional) Sort order; can be either 'ASC' or 'DESC'
                    (default: 'ASC')
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: (list) Dictionaries of group properties
             - totalCount: (integer) Number of devices returned
        """
        facade = self._getFacade()
        groups = facade.getGroups(start=start, limit=limit, sort=sort, dir=dir, name=name)
        total = groups.total
        data = Zuul.marshal(groups, keys)
        return DirectResponse.succeed(data=data, totalCount=total)
        pass

    @require('Manage DMD')
    def createGroups(self, groups):
        """
        Adds a new group to the system.
        @type  groups: list of string
        @param groups: The unique names of each group
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: properties of the new users
        """
        facade = self._getFacade()
        newGroups = facade.createGroups(groups)
        audit('UI.Users.CreateGroups', groups)
        return DirectResponse.succeed(data=Zuul.marshal(newGroups))

    @require('Manage DMD')
    def deleteGroups(self, groups):
        """
        Removes all the users from the given group then deletes the group.
        @type  groups: List of Strings
        @param groups: (optional) group ids to remove.
        """
        facade = self._getFacade()
        facade.removeGroups(groups)
        audit('UI.Users.RemoveGroups', groupIds=groups)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def listGroupsForUser(self, users):
        """
        Lists all the groups for each provided user.
        @type  users: List of Strings
        @param users: user ids to get group info.
        """
        facade = self._getFacade()
        usermap = facade.listGroupsForEachUser(users)
        total = len(usermap)
        data = Zuul.marshal(usermap)
        audit('UI.Users.ListGroupsForUser', userIds=users)
        return DirectResponse.succeed(data=data, totalCount=total)

    @require('Manage DMD')
    def listUsersInGroup(self, groups):
        """
        Lists all the users belonging to each provided group.
        @type  groups: List of Strings
        @param groups: groups to get user ids.
        """
        facade = self._getFacade()
        groupmap = facade.listGroupMembers(groups)
        total = len(groupmap)
        data = Zuul.marshal(groupmap)
        audit('UI.Users.ListUsersInGroup', groupIds=groups)
        return DirectResponse.succeed(data=data, totalCount=total)

    @require('Manage DMD')
    def addUsersToGroups(self, users, groups):
        """
        Adds listed users to the given group.
        @type  users: List of Strings
        @param users: (optional) user ids to add to groups.
        @type  groups: List of Strings
        @param groups: (optional) group ids users will be added to.
        """
        facade = self._getFacade()
        facade.addUsersToGroups(users, groups)
        audit('UI.Users.AddUsersToGroups', userIds=users, groupIds=groups)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeUsersFromGroups(self, users, groups):
        """
        Removes listed users from the given group.
        @type  users: List of Strings
        @param users: (optional) user ids to add to groups.
        @type  groups: List of Strings
        @param groups: (optional) group ids users will be removed from.
        """
        facade = self._getFacade()
        facade.removeUsersFromGroups(users, groups)
        audit('UI.Users.RemoveUsersFromGroups', userIds=users, groupIds=groups)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def assignZenUserRoleToUsers(self, users):
        """
        Assign the ZenUser role to the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to assign zenuser roles to.
        """
        facade = self._getFacade()
        facade.assignZenUserRoleToUsers(users)
        audit('UI.Users.AssignZenUserRoleToUsers', userIds=users)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeZenUserRoleFromUsers(self, users):
        """
        Removes the ZenUser role from the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to remove zenuser role from.
        """
        facade = self._getFacade()
        facade.removeZenUserRoleFromUsers(users)
        audit('UI.Users.RemoveZenUserRoleFromUsers', userIds=users)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def assignAdminRolesToUsers(self, users):
        """
        Assign the admin roles to the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to assign admin roles to.
        """
        facade = self._getFacade()
        facade.assignAdminRolesToUsers(users)
        audit('UI.Users.AssignAdminRolesToUsers', userIds=users)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeAdminRolesFromUsers(self, users):
        """
        Removes the admin roles from the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to remove admin roles from.
        """
        facade = self._getFacade()
        facade.removeAdminRolesFromUsers(users)
        audit('UI.Users.RemoveAdminRolesFromUsers', userIds=users)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addAdministeredObject(self, users, groups, objname, guid, uid):
        """
        Include the provided object to the list of Adminstered Objects for the users and/or groups.
        @type  users: List of Strings
        @param users: (optional) user ids to assign admin roles to.
        @type  groups: List of Strings
        @param groups: (optional) group ids users will be removed from.
        @type  objname: String
        @param objname: (optional) name of the device/object to be administered by user/group
        @type  guid: String
        @param guid: (optional) guid for a device/object to be administered by user/group
        @type  uid: String
        @param uid: (optional) uid for a device/object to be administered by user/group
        """
        facade = self._getFacade()
        facade.addAdministeredObject(users, groups, objname, guid, uid)
        audit('UI.Users.AddAdministeredObject', userIds=users, groupids=groups, name=objname, guid=guid, uid=uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeAdministeredObject(self, users, groups, objname, guid, uid):
        """
        Exclude the provided object to the list of Adminstered Objects for the users and/or groups.
        @type  users: List of Strings
        @param users: (optional) user ids to remove admin roles from.
        @type  groups: List of Strings
        @param groups: (optional) group ids users will be removed from.
        @type  objname: String
        @param objname: (optional) name of the device/object to be administered by user/group
        @type  guid: String
        @param guid: (optional) guid for a device/object to be administered by user/group
        @type  uid: String
        @param uid: (optional) uid for a device/object to be administered by user/group
        """
        facade = self._getFacade()
        facade.removeAdministeredObject(users, groups, objname, guid, uid)
        audit('UI.Users.RemoveAdministeredObject', userIds=users, groupids=groups, name=objname, guid=guid, uid=uid)
        return DirectResponse.succeed()
