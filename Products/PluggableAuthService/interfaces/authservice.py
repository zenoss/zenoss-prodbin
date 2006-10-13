##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Interfaces:  IUser, IUserFolder, IMutableUserFolder, IEnumerableUserFolder

$Id: authservice.py 67172 2006-04-20 11:52:41Z jens $
"""

try:
    from zope.interface import Interface
except ImportError:
    from Interface import Interface
from AccessControl.ZopeSecurityPolicy import _noroles


class IBasicUser( Interface ):

    """ Specify the interface called out in AccessControl.User.BasicUser
        as the "Public User object interface", except that '_getPassword'
        is *not* part of the contract!
    """

    def getId():

        """ Get the ID of the user.

        o The ID can be used, at least from Python, to get the user from
          the user's UserDatabase
        """

    def getUserName():

        """ Return the name used by the user to log into the system.

        o Note that this may not be identical to the user's 'getId'
          (to allow users to change their login names without changing
          their identity).
        """

    def getRoles():

        """ Return the roles assigned to a user "globally".
        """

    def getRolesInContext( object ):

        """ Return the roles assigned to the user in context of 'object'.

        o Roles include both global roles (ones assigned to the user
          directly inside the user folder) and local roles (assigned
          in context of the passed in object.
        """

    def getDomains():

        """ Return the list of domain restrictions for a user.
        """


class IPropertiedUser( IBasicUser ):

    """ A user which has property sheets associated with it,
        i.e. a mapping from strings (property sheet ids)
        to objects implementing IPropertySheet
    """

    def listPropertysheets():

        """ Return a sequence of property sheet ids

        o for each id in the list getPropertysheet(id)
          returns a IPropertySheet
        """

    def getPropertysheet( id ):

        """ Return a property sheet for the given id

        o the returned object implements IPropertySheet
          and has the same id as the value passed to this method

        o if there is no property sheet for the given id,
          raise a KeyError

          An alternative way to get the property sheet is via item access,
          i.e. user.getPropertysheet( id ) == user[ id ]
        """


class IUserFolder( Interface ):

    """ Specify the interface called out in AccessControl.User.BasicUserFolder
        as the "Public UserFolder object interface":

    o N.B: "enumeration" methods ('getUserNames', 'getUsers') are *not*
           part of the contract!  See IEnumerableUserFolder.
    """

    def getUser( name ):

        """ Return the named user object or None.
        """

    def getUserById( id, default=None ):

        """ Return the user corresponding to the given id.

        o If no such user can be found, return 'default'.
        """

    def validate( request, auth='', roles=_noroles ):

        """ Perform identification, authentication, and authorization.

        o Return an IUser-conformant user object, or None if we can't
          identify / authorize the user.

        o 'request' is the request object

        o 'auth' is any credential information already extracted by
          the caller

        o roles is the list of roles the caller
        """

class IPluggableAuthService( IUserFolder ):

    """ The full, default contract for the pluggable authentication service.
    """

    def searchUsers(**kw):

        """ Search for users.  Returns a sequence of dicts, each dict
        representing a user matching the query, with the keys
        'userid','id', 'login', 'title', and 'principal_type',
        possibly among others.  'principal_type' is always 'user'.

        Possible keywords include the following:

        o id: user id

        o name: user name

        o max_results: an int (or value castable to int) indicating
          the maximum number of results the method should return

        o sort_by: the key in the user dictionary that should be used
          to sort the results

        o login: user login
        """

    def searchGroups(**kw):
        """ Search for groups.  Returns a sequence of dicts, each dict
        representing a group matching the query, with the keys
        'groupid','id', 'title', and 'principal_type', possibly among
        others.  'principal_type' is always 'group'.

        Possible keywords include the following:

        o id: user id

        o name: user name

        o max_results: an int (or value castable to int) indicating
          the maximum number of results the method should return

        o sort_by: the key in the user dictionary that should be used
          to sort the results
        """

    def searchPrincipals(groups_first=False, **kw):
        """ Search for principals (users, groups, or both).  Returns a
        sequence of dicts, each dict representing a principal (group
        or user) matching the query.  groups will be represented with
        dictionaries as described in searchGroups, and users as
        described in searchUsers.  Possible keywords include id, name,
        max_results, sort_by, and login.
        """

    def updateCredentials(request, response, login, new_password):
        """Central updateCredentials method

        This method is needed for cases where the credentials storage
        and the credentials extraction is handled by different
        plugins. Example case would be if the CookieAuthHelper is used
        as a Challenge and Extraction plugin only to take advantage of
        the login page feature but the credentials are not stored in
        the CookieAuthHelper cookie but somewhere else, like in a
        Session.
        """

    def logout(REQUEST):
        """Publicly accessible method to log out a user. A wrapper
        around resetCredentials that may implement some policy (the
        default implementation redirects to HTTP_REFERER).
        """

    def resetCredentials(self, request, response):
        """Reset credentials by informing all active resetCredentials
        plugins
        """

# The IMutableUserFolder and IEnumerableFolder are not supported
# out-of-the-box by the pluggable authentication service.  These
# interfaces describe contracts that other standard Zope user folders
# implement.

class IMutableUserFolder( Interface ):

    """ Specify the interface called out in
        AccessControl.User.BasicUserFolder as the
        "Public UserFolder object interface":

    o N.B: "enumeration" methods ('getUserNames', 'getUsers') are *not*
           part of the contract!  See IEnumerableUserFolder.
    """

    def userFolderAddUser( name, password, roles, domains, **kw ):

        """ Create a new user object.
        """

    def userFolderEditUser( name, password, roles, domains, **kw ):

        """ Change user object attributes.
        """

    def userFolderDelUsers( names ):

        """ Delete one or more user objects.
        """

class IEnumerableUserFolder( IUserFolder ):

    """ Interface for user folders which can afford to enumerate their users.
    """

    def getUserNames():

        """ Return a list of usernames.
        """

    def getUsers():

        """ Return a list of user objects.
        """
