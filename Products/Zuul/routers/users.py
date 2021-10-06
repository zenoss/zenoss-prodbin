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
    def addUser(self, name, password, email, groups=(), roles=('ZenUser',)):
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

    def assignAdminRolesToUsers(self, users):
        """
        Assign the listed roles to the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to assign admin roles to.
        """
        facade = self._getFacade()
        facade.assignAdminRolesToUsers(users)
        audit('UI.Users.AssignAdminRolesToUsers', userIds=users)
        return DirectResponse.succeed()

    def removeAdminRolesFromUsers(self, users):
        """
        Removes the listed roles from the given users.
        @type  users: List of Strings
        @param users: (optional) user ids to remove admin roles from.
        """
        facade = self._getFacade()
        facade.removeAdminRolesFromUsers(users)
        audit('UI.Users.RemoveAdminRolesFromUsers', userIds=users)
        return DirectResponse.succeed()
