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
""" Interfaces for PluggableAuthService

$Id: plugins.py 69827 2006-08-29 03:21:16Z tseaver $
"""

try:
    from zope.interface import Interface
except ImportError:
    from Interface import Interface

class IExtractionPlugin( Interface ):

    """ Extracts login name and credentials from a request.
    """

    def extractCredentials( request ):

        """ request -> {...}

        o Return a mapping of any derived credentials.

        o Return an empty mapping to indicate that the plugin found no
          appropriate credentials.
        """

class ILoginPasswordExtractionPlugin( IExtractionPlugin ):

    """ Common-case derivative.
    """

    def extractCredentials( request ):

        """ request -> { 'login' : login 
                       , 'password' : password 
                       , k1 : v1
                       ,   ...
                       , kN : vN
                       } | {}

        o If credentials are found, the returned mapping will contain at
          least 'login' and 'password' keys, with the password in plaintext.

        o Return an empty mapping to indicate that the plugin found no
          appropriate credentials.
        """

class ILoginPasswordHostExtractionPlugin( ILoginPasswordExtractionPlugin ):

    """ Common-case derivative.
    """

    def extractCredentials( request ):

        """ request -> { 'login' : login 
                       , 'password' : password 
                       , 'remote_host' : remote_host
                       , 'remote_addr' : remote_addr
                       , k1 : v1
                       ,   ...
                       , kN : vN
                       } | {}

        o If credentials are found, the returned mapping will contain at
          least 'login', 'password', 'remote_host' and 'remote_addr' keys,
          with the password in plaintext.

        o Return an empty mapping to indicate that the plugin found no
          appropriate credentials.
        """

class IAuthenticationPlugin( Interface ):

    """ Map credentials to a user ID.
    """

    def authenticateCredentials( credentials ):

        """ credentials -> (userid, login)

        o 'credentials' will be a mapping, as returned by IExtractionPlugin.

        o Return a  tuple consisting of user ID (which may be different 
          from the login name) and login

        o If the credentials cannot be authenticated, return None.
        """

class IChallengePlugin( Interface ):

    """ Initiate a challenge to the user to provide credentials.

        Challenge plugins have an attribute 'protocol' representing
        the protocol the plugin operates under, defaulting to None.

        Plugins operating under the same protocol will all be given an
        attempt to fire. The first plugin of a protocol group that
        successfully fires establishes the protocol of the overall
        challenge.
    """

    def challenge( request, response ):

        """ Assert via the response that credentials will be gathered.

        Takes a REQUEST object and a RESPONSE object.

        Returns True if it fired, False otherwise.

        Two common ways to initiate a challenge:

          - Add a 'WWW-Authenticate' header to the response object.

            NOTE: add, since the HTTP spec specifically allows for
            more than one challenge in a given response.

          - Cause the response object to redirect to another URL (a
            login form page, for instance)
        """

class ICredentialsUpdatePlugin( Interface ):

    """ Callback:  user has changed her password.
    """

    def updateCredentials( request, response, login, new_password ):

        """ Scribble as appropriate.
        """

class ICredentialsResetPlugin( Interface ):

    """ Callback:  user has logged out.
    """

    def resetCredentials( request, response ):

        """ Scribble as appropriate.
        """

class IUserAdderPlugin( Interface ):

    """ Create a new user record in a User Manager
    """

    def doAddUser( login, password ):

        """ Add a user record to a User Manager, with the given login
            and password

        o Return a Boolean indicating whether a user was added or not
        """

class IRoleAssignerPlugin( Interface ):

    """ Assign a role to an identified principal
    """

    def doAssignRoleToPrincipal( principal_id, role ):

        """ Create a principal/role association in a Role Manager

        o Return a Boolean indicating whether the role was assigned or not
        """

class IUserFactoryPlugin( Interface ):

    """ Create a new IPropertiedUser.
    """

    def createUser( user_id, name ):

        """ Return a user, if possible.

        o Return None to allow another plugin, or the default, to fire.
        """

class IAnonymousUserFactoryPlugin( Interface ):

    """ Create a new anonymous IPropertiedUser.
    """

    def createAnonymousUser():

        """ Return an anonymous user, if possible.

        o Return None to allow another plugin, or the default, to fire.
        """

class IPropertiesPlugin( Interface ):

    """ Return a property set for a user.
    """

    def getPropertiesForUser( user, request=None ):

        """ user -> {}

        o User will implement IPropertiedUser.

        o Plugin may scribble on the user, if needed (but must still
          return a mapping, even if empty).

        o May assign properties based on values in the REQUEST object, if
          present
        """

class IGroupsPlugin( Interface ):

    """ Determine the groups to which a user belongs.
    """

    def getGroupsForPrincipal( principal, request=None ):

        """ principal -> ( group_1, ... group_N )

        o Return a sequence of group names to which the principal 
          (either a user or another group) belongs.

        o May assign groups based on values in the REQUEST object, if present
        """

class IRolesPlugin( Interface ):

    """ Determine the (global) roles which a user has.
    """

    def getRolesForPrincipal( principal, request=None ):

        """ principal -> ( role_1, ... role_N )

        o Return a sequence of role names which the principal has.

        o May assign roles based on values in the REQUEST object, if present.
        """

class IUpdatePlugin( Interface ):

    """ Allow the user or the application to update the user's properties.
    """

    def updateUserInfo( user, set_id, set_info ):

        """ Update backing store for 'set_id' using 'set_info'.
        """

class IValidationPlugin( Interface ):

    """ Specify allowable values for user properties.

    o E.g., constrain minimum password length, allowed characters, etc.

    o Operate on entire property sets, not individual properties.
    """

    def validateUserInfo( user, set_id, set_info ):

        """ -> ( error_info_1, ... error_info_N )

        o Returned values are dictionaries, containing at least keys:

          'id' -- the ID of the property, or None if the error is not
                  specific to one property.

          'error' -- the message string, suitable for display to the user.
        """

class IUserEnumerationPlugin( Interface ):

    """ Allow querying users by ID, and searching for users.

    o XXX:  can these be done by a single plugin?
    """

    def enumerateUsers( id=None
                      , login=None
                      , exact_match=False
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):

        """ -> ( user_info_1, ... user_info_N )

        o Return mappings for users matching the given criteria.

        o 'id' or 'login', in combination with 'exact_match' true, will
          return at most one mapping per supplied ID ('id' and 'login'
          may be sequences).

        o If 'exact_match' is False, then 'id' and / or login may be
          treated by the plugin as "contains" searches (more complicated
          searches may be supported by some plugins using other keyword
          arguments).

        o If 'sort_by' is passed, the results will be sorted accordingly.
          known valid values are 'id' and 'login' (some plugins may support
          others).

        o If 'max_results' is specified, it must be a positive integer,
          limiting the number of returned mappings.  If unspecified, the
          plugin should return mappings for all users satisfying the criteria.

        o Minimal keys in the returned mappings:
        
          'id' -- (required) the user ID, which may be different than
                  the login name

          'login' -- (required) the login name

          'pluginid' -- (required) the plugin ID (as returned by getId())

          'editurl' -- (optional) the URL to a page for updating the
                       mapping's user

        o Plugin *must* ignore unknown criteria.

        o Plugin may raise ValueError for invalid criteria.

        o Insufficiently-specified criteria may have catastrophic
          scaling issues for some implementations.
        """

class IGroupEnumerationPlugin( Interface ):

    """ Allow querying groups by ID, and searching for groups.

    o XXX:  can these be done by a single plugin?
    """

    def enumerateGroups( id=None
                       , exact_match=False
                       , sort_by=None
                       , max_results=None
                       , **kw
                       ):

        """ -> ( group_info_1, ... group_info_N )

        o Return mappings for groups matching the given criteria.

        o 'id' in combination with 'exact_match' true, will
          return at most one mapping per supplied ID ('id' and 'login'
          may be sequences).

        o If 'exact_match' is False, then 'id' may be treated by 
          the plugin as "contains" searches (more complicated searches 
          may be supported by some plugins using other keyword arguments).

        o If 'sort_by' is passed, the results will be sorted accordingly.
          known valid values are 'id' (some plugins may support others).

        o If 'max_results' is specified, it must be a positive integer,
          limiting the number of returned mappings.  If unspecified, the
          plugin should return mappings for all groups satisfying the 
          criteria.

        o Minimal keys in the returned mappings:
        
          'id' -- (required) the group ID

          'pluginid' -- (required) the plugin ID (as returned by getId())

          'properties_url' -- (optional) the URL to a page for updating the
                              group's properties.

          'members_url' -- (optional) the URL to a page for updating the
                           principals who belong to the group.

        o Plugin *must* ignore unknown criteria.

        o Plugin may raise ValueError for invalid critera.

        o Insufficiently-specified criteria may have catastrophic
          scaling issues for some implementations.
        """

class IRoleEnumerationPlugin( Interface ):

    """ Allow querying roles by ID, and searching for roles.
    """
    def enumerateRoles( id=None
                      , exact_match=False
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):

        """ -> ( role_info_1, ... role_info_N )

        o Return mappings for roles matching the given criteria.

        o 'id' in combination with 'exact_match' true, will
          return at most one mapping per supplied ID ('id' and 'login'
          may be sequences).

        o If 'exact_match' is False, then 'id' may be treated by 
          the plugin as "contains" searches (more complicated searches 
          may be supported by some plugins using other keyword arguments).

        o If 'sort_by' is passed, the results will be sorted accordingly.
          known valid values are 'id' (some plugins may support others).

        o If 'max_results' is specified, it must be a positive integer,
          limiting the number of returned mappings.  If unspecified, the
          plugin should return mappings for all roles satisfying the 
          criteria.

        o Minimal keys in the returned mappings:
        
          'id' -- (required) the role ID

          'pluginid' -- (required) the plugin ID (as returned by getId())

          'properties_url' -- (optional) the URL to a page for updating the
                              role's properties.

          'members_url' -- (optional) the URL to a page for updating the
                           principals to whom the role is assigned.

        o Plugin *must* ignore unknown criteria.

        o Plugin may raise ValueError for invalid critera.

        o Insufficiently-specified criteria may have catastrophic
          scaling issues for some implementations.
        """

class IRequestTypeSniffer( Interface ):

    """ Given a request, detects the request type for later use by other plugins.
    """
    def sniffRequestType( request ):
        """ Return a interface identifying what kind the request is.
        """

class IChallengeProtocolChooser( Interface ):

    """ Choose a proper set of protocols to be used for challenging
    the client given a request.
    """
    def chooseProtocols( request ):
        """ -> ( protocol_1, ... protocol_N) | None
        
        o If a set of protocols is returned, the first plugin with a
            protocol that is in the set will define the protocol to be
            used for the current request.

        o If None is returned, the 'first found protocol' wins.

        o Once the protocol is decided, all challenge plugins for that
            protocol will be executed.
        """
#
#   XXX:  Do we need a LocalRoleAlgorithm plugin type?  E.g., base_cms
#         has two different algorithms, based on whether or not the
#         context object implements IPlacelessSecurity.
#
