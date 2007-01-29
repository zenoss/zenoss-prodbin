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
""" CMFCore tool interfaces.

$Id: _tools.py 40047 2005-11-11 09:06:05Z yuppie $
"""

from zope.interface import Interface
from zope.interface import Attribute

_marker = object()


#
#   Action subsystem interfaces
#
class IActionsTool(Interface):

    """ Generate the list of "actions" which the user is allowed to perform.

    o Synthesize this list from the actions managed by a set of "action
      providers".
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IActionsTool)'.

            o Must be set to "portal_actions"
            """,
            )

    def listActionProviders():
        """ Return a sequence of names of all IActionProvider utilities
            registered with this tool.

        o The returned list of names will be a subset of the set available
          via 'zapi.getUtilitiesFor(IActionProvider)' (which returns
          '(name, value)' tuples).

        o Deprecated: In the future, expect to use 'getUtilitiesFor' instead
          (presuming either that ordering either doesn't matter or that
          ordering is supported by the utility registry).

        o Permission:  Manage portal
        """

    def addActionProvider(provider_name):
        """ Register an IActionProvider to the set queried by this tool.

        o 'provider_name' is appended to the set of names already registered
          with the tool.

        o Raise ComponentLookupError if no utility of that name is registered
          for IActionProvider.

        o Deprecated: In the future, expect to use 'getUtilitiesFor' instead
          (presuming either that ordering either doesn't matter or that
          ordering is supported by the utility registry).

        o Permission:  Manage portal
        """

    def deleteActionProvider(provider_name):
        """ Remove an IActionProvider from the set queried by this tool.

        o Return silently if 'provider_name' is not already registered with
          the tool.

        o Deprecated: In the future, expect to use 'getUtilitiesFor' instead
          (presuming either that ordering either doesn't matter or that
          ordering is supported by the utility registry).

        o Permission:  Manage portal
        """

    def listFilteredActionsFor(object=None):
        """ Map actions available to the user by category.

        o Returned mapping will have category IDs as keys, and sequences
          of IActionInformation objects as the corresponding values for each
          category.

        o Categories may be arbitrarily extended.

        o Permission:  Public
        """


class IActionProvider(Interface):

    """ Objects that can be queried for actions.
    """

    def listActions(info=None, object=None):
        """ List known action informations.

        o Return a sequence of IActionInformation intances.

        o Both the 'object' and the 'info' arguments are deprecated and
          ignored (use 'listActionInfos' to filter actions by context).
        """

    def listActionInfos(action_chain=None, object=None, check_visibility=True,
                        check_permissions=True, check_condition=True, max=None):
        """ Return a sequence of IActionInformation matching the given criteria.

        o 'action_chain' is a sequence of one or more action paths
          (e.g. 'object/view');  each path is formatted as
          'category_id/action_id'.  If specified, only matching actions will
          be returned, and in the given order (paths with no matches are
          ignored silently).

        o If 'object' is specified, only actions specific to that object
          are included.

        o If 'check_visibility' is True, return only actions whos "visible"
          flag is set.

        o If 'check_permissions' is True, return only actions for whose
          permissions the current user is authorized.

        o If 'check_condition' is True, return only actions whose condition
          expression evaluates True.

        o If 'max' is specified, return only the first 'max' Actions.

        o Permission:  Public (but not URL-publishable)
        """

    def getActionInfo(action_chain, object=None, check_visibility=False,
                      check_condition=False):
        """ Return the first IActionInformation matching the given criteria.

        o If no action is found matching the criteria, raise ValueError.

        o 'action_chain' is a sequence of one or more action paths
          (e.g. 'object/view');  each path is formatted as
          'category_id/action_id'.  If specified, only matching actions will
          be returned, and in the given order (paths with no matches are
          ignored silently).

        o If 'check_visibility' is True, return only actions whos "visible"
          flag is set.

        o If 'check_condition' is True, return only actions whose condition
          expression evaluates True.

        o Permission:  Public
        """


class IActionCategory(Interface):

    """ Group of IAction objects and child categories.
    """

    def listActions():
        """ Return a sequence of IActionInformation defined by this category

        o Include actions defined by subcategories.

        o Permission:  Private (Python only)
        """


class IAction(Interface):

    """ Specification for an action.
    """

    def getInfoData():
        """ Return a lazy mapping of the data needed to create an
            IActionInformation.

        o Returned value is actually a tuple, '(lazy_map, lazy_keys)'.

        o Default keys are: 'id', 'category', 'title', 'description', 'url',
          'icon', 'available', 'permissions' and 'visible'.

        o Instead of computed values callable expression objects or methods
          are returned. For performance reasons, these objects are called
          later and only if the values are actually needed. The keys for all
          these lazy values are registered in a separate list.
        """


class IActionInfo(Interface):

    """ A lazy dictionary for Action infos.

    o Each ActionInfo object has the following keys:

      - id (string): not unique identifier

      - title (string)

      - url (string): URL to access the action

      - category (string): one of "user", "folder", "object", "global",
        "workflow" or a custom category

      - visible (boolean)

      - available (boolean): the result of checking the condition

      - allowed (boolean): the result of checking permissions;
        The user must have at least one of the listed permissions to access
        the action. If the list is empty, the user is allowed.
    """


#
#   Caching policy tool interfaces
#
class ICachingPolicy(Interface):

    def getPolicyId():
        """
        """

    def getPredicate():
        """
        """

    def getMTimeFunc():
        """
        """

    def getMaxAgeSecs():
        """
        """

    def getSMaxAgeSecs():
        """
        """

    def getNoCache():
        """
        """

    def getNoStore():
        """
        """

    def getMustRevalidate():
        """
        """

    def getProxyRevalidate():
        """
        """

    def getPublic():
        """
        """

    def getPrivate():
        """
        """

    def getNoTransform():
        """
        """

    def getVary():
        """
        """

    def getETagFunc():
        """
        """

    def getEnable304s():
        """
        """

    def getLastModified():
        """Should we set the last modified header?
        """

    def getPreCheck():
        """
        """

    def getPostCheck():
        """
        """
    
    def testPredicate(expr_context):
        """Does this request match our predicate?
        """

    def getHeaders(expr_context):
        """Does this request match our predicate?

        If so, return a sequence of caching headers as (key, value) tuples.
        Otherwise, return an empty sequence.
        """


class ICachingPolicyManager(Interface):

    """ Compute HTTP cache headers for skin methods.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
                    'zapi.getUtility(ICachingPolicyManager)'.

            o Must be set to 'caching_policy_manager'.
            """,
            )

    def getHTTPCachingHeaders(content, view_method, keywords, time=None):
        """ Update HTTP caching headers in REQUEST

        o 'content' is the content object being published.

        o 'view_method' is the name of the view being published

        o 'keywords' is a set of extra keywords modifying the view.

        o If 'time' is supplied, use it instead of the current time
          (for reliable testing).
        """


#
#   Catalog tool interfaces
#
class ICatalogTool(Interface):

    """Wrap the "stock" ZCatalog with custom behavior for the CMF.
    """

    id = Attribute('id', 'Must be set to "portal_catalog"')

    # searchResults inherits security assertions from ZCatalog.
    def searchResults(REQUEST=None, **kw):
        """ Decorate ZCatalog.searchResults() with extra arguments

        o The extra arguments that the results to what the user would be
          allowed to see.
        """

    # __call__ inherits security assertions from ZCatalog.
    def __call__(REQUEST=None, **kw):
        """Alias for searchResults().
        """

    def unrestrictedSearchResults(REQUEST=None, **kw):
        """Calls ZCatalog.searchResults() without any CMF-specific processing.

        o Permission:  Private (Python only)
        """

    def indexObject(object):
        """ Add 'object' to the catalog.

        o Permission:  Private (Python only)
        """

    def unindexObject(object):
        """ Remove 'object' from the catalog.

        o Permission:  Private (Python only)
        """

    def reindexObject(object, idxs=[], update_metadata=True):
        """ Update 'object' in catalog.

        o 'idxs', if passed, is a list of specific indexes to update
          (by default, all indexes are updated).

        o If 'update_metadata' is True, then update the metadata record
          in the catalog as well.

        o Permission:  Private (Python only)
        """


class IIndexableObjectWrapper(Interface):

    """ Wrapper for catalogued objects, for indexing "virtual" attributes.
    """

    def allowedRolesAndUsers():
        """ Return a sequence roles and users with View permission.

        o PortalCatalog indexes this sequence to allow filtering out items
          a user is not allowed to see.
        """


#
#   PUT factory handler interfaces
#
class IContentTypeRegistryPredicate(Interface):

    """ Match a given name/typ/body to a portal type.

    The registry will call the predictate's 'edit' method, passing the fields
    of the record.
    """

    def __call__(name, typ, body):
        """ Return true if the rule matches, else false. """

    def getTypeLabel():
        """ Return a human-readable label for the predicate type. """

    def predicateWidget():
        """ Return a snippet of HTML suitable for editing the predicate.

        o This method may be defined via DTMLFile or PageTemplateFile
          (the tool will call it appropriately, if it is DTML).

        o The snippet should arrange for values to be marshalled by
          ZPublisher as a ':record', with the ID of the predicate as the
          name of the record.
        """


class IContentTypeRegistry(Interface):

    """ Apply policy mapping PUT arguments to a CMF portal type.
    """

    def findTypeName(name, typ, body):
        """ Return the the portal type (an ID) for a PUT request.

        o 'name' is the filename supplied as the end of the path of the
          PUT request.

        o 'typ' is the MIME type for the request (which may have been guessed
          already from the extension or the body).

        o 'body' is the actual payload of the PUT request.

        o Return None if no match found.
        """


#
#   Cookie crumbler interfaces.
#
class ICookieCrumbler(Interface):

    """Reads cookies during traversal and simulates the HTTP auth headers.
    """


#
#   Discussion tool interfaces.
#
class IOldstyleDiscussionTool(Interface):

    """ Links content to discussions.
    """

    id = Attribute('id',
            """ The tool's ID.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IDiscussionTool)'.

            o Must be set to 'portal_discussion'.
            """)

    def getDiscussionFor(content):
        """ Return an IDiscussionItemContainer for 'content'.

        o Create the IDC if necessary.

        o Raise ValueError if discussion is not allowed on 'content'.

        o Permission:  Public
        """

    def isDiscussionAllowedFor(content):
        """ Return True discussion is allowed for 'content', else False.

        o Result may be looked up from an object-specific value, or by place,
          or from a site-wide policy.

        o Permission:  Public
        """


class IDiscussionTool(IOldstyleDiscussionTool):

    """ Links content to discussions.
    """

    def overrideDiscussionFor(content, allowDiscussion):
        """ Override discussability for the given object or clear the setting.

        o 'allowDiscussion' may be True, False, or None.

        o If 'allowDiscussion' is None, then clear any overridden setting for
          discussability, letting the site's default policy apply.

        o Otherwise, set the override to match 'allowDiscussion'.

        o Permission:  PUblic XXX?  Should be ManageContent, or something.
        """


#
#   MemberData tool interfaces
#
class IMemberDataTool(Interface):

    """ Decorate user objects with site-local data.
    """

    id = Attribute('id',
            """ The tool's ID.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IMemberDataTool)'.

            o Must be set to 'portal_memberdata'
            """,
            )

    def wrapUser(user):
        """Returns an IMember corresponding to the given user object.

        o Permission:  Private (Python-only)
        """

    def getMemberDataContents():
        """ Returns a list containing a dictionary with information
        about the _members BTree contents

        o The key 'member_count' is the total number of member instances
          stored in the memberdata-tool

        o The key 'orphan_count' is the number of member instances
          that for are no longer in the underlying acl_users user folder.

        o The result is designed to be iterated over in a dtml-in

        o XXX:  why a sequence?

        o Permission:  Private (Python-only)
        """

    def pruneMemberDataContents():
        """ Delete member data of all members not findable in acl_users.

        o Compare the user IDs stored in the member data tool with the
          list in the actual underlying acl_users and delete any records whose
          user cannot be found.

        o Permission:  Private (Python only)
        """

    def searchMemberData(search_param, search_term, attributes=()):
        """ Return a sequence of mappings of memberdata for the given criteria.

        o 'search_param' is the property ID to be searched.

        o 'search_term' is the property value to be searched.

        o 'attributes', if passed, controls the keys in the returned mappings;
          by default the returned keys are 'username' and 'email'.

        o XXX:  that default is silly;  if it is truly needed, then it should
          be the default value of the 'attributes' argument.

        o Permission:  Private (Python only)
        """

    def registerMemberData(m, id):
        """ Add the given member data to the _members btree.

        o 'm' is an object whose attributes are the memberdata for the member.

        o 'id' is the userid of the member.

        o Add the record late as possible to avoid side effect transactions
          and to reduce the necessary number of entries.

        o XXX: these argument names are silly;  can we use more sensible
          ones (i.e., does anyone actually depend on them)?

        o Permission:  Private (Python only)
        """

    def deleteMemberData(member_id):
        """ Delete member data of specified member.

        o Return True if a record was deleted, else False.

        o Permission:  Private (Python only)
        """

class IMemberData(Interface):

    """ MemberData interface.
    """

    def setProperties(properties=None, **kw):
        """ Allow the authenticated member to update his/her member data.

        o 'properties', if passed, is a mapping of the IDs and values of
          the properties to be changed.

        o The method may also be invoked via keyword arguments (in this
          case, do *not* pass 'properties').

        o Permission:  Set own properties
        """


#
#   Membership tool interfaces
#
class IMembershipTool(Interface):

    """ Manage policy of how and where to store and retrieve members and
        their member folders.
    """

    id = Attribute('id',
            """ The tool's ID.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IMembershipTool)'.

            o Must be set to 'portal_membership'.
            """)

    def setPassword(password, domains=None):
        """ Allow the authenticated member to set his/her own password.

        Permission:  Set own password
        """

    def getAuthenticatedMember():
        """ Return the currently authenticated member object

        o If no valid credentials are passed in the request, return
          the Anonymous User.

        o Permission:  Public
        """

    def isAnonymousUser():
        """ Return True if no valid credentials are passed in the requeset.

        o Permission:  Public
        """

    def checkPermission(permissionName, object, subobjectName=None):
        """ Return True if the current user has the given permission on
            the given object or subobject.

        o 'permissionName' is the string identifying the permission.

        o 'object' is the object being checked.

        o 'subobjectName', if passed, is the attribute name to be checked;
          if None, test the main object itself.

        o Permission:  Public
        """

    def credentialsChanged(password):
        """ Notify the authentication mechanism that this user has
            changed passwords.

        o The authentication mechanism can use this notification to update
          the authentication cookie.

        o Note that this call should *not* cause any change at all to user
          databases.

        o XXX:  should be an event.

        o XXX:  should this be in scope for this tool?  Or should it be
                done by the view class for the password update view?

        Permission:  Public # XXX?
        """

    def getMembersFolder():
        """ Return the folderish object which contains membmer folders.

        o Return None if no members folder is set or if the specified
          folder doesn't exist.

        o Permission:  Public
        """

    def getHomeFolder(id=None, verifyPermission=False):
        """ Return a member's home folder object or None.

        o 'id', if passed, is the ID of the member whose folder should be
          returned;  if not passed, use the currently-authenticated member.

        o If 'verifyPermission' is True, return None when the user
          doesn't have the View permission on the folder.

        o Permission:  Public
        """

    def getHomeUrl(id=None, verifyPermission=0):
        """ Return the URL to a member's home folder or None.

        o 'id', if passed, is the ID of the member whose folder should be
          returned;  if not passed, use the currently-authenticated member.

        o If 'verifyPermission' is True, return None when the user
          doesn't have the View permission on the folder.

        Permission:  Public
        """

    def getMemberById(id):
        """ Returns the given IMember.

        o Permission:  Manage users
        """

    def listMemberIds():
        """ Return a sequence of ids of all members.

        o This may eventually be replaced with a set of methods for querying
          pieces of the list rather than the entire list at once.

        o Permission:  Manage users
        """

    def listMembers():
        """ Return a sequence of all IMembers.

        o This may eventually be replaced with a set of methods for querying
          pieces of the list rather than the entire list at once.

        o Permission:  Manage users
        """

    def getCandidateLocalRoles(obj):
        """ Return a sequence local roles assignable by the current user for
            a given object.

        o 'obj' is the object to which role assignments may be made.

        o Permission:  Public # XXX?
        """

    def setLocalRoles(obj, member_ids, member_role, reindex=True):
        """ Assign a local role on an item to one or more members.

        o 'obj' is the object on which to assign the role.

        o 'member_ids' is a sequence of user IDs to which to assign the role.

        o 'member_role' is the name of the role to assign.

        o If 'reindex' is True, then reindex the security-related attributes
          of the object and all subobjects.

        o Raise Unauthorized if the currently-authenticated member cannot
          assign 'member_role' on 'obj'.

        o Permission:  Public # XXX?
        """

    def deleteLocalRoles(obj, member_ids, reindex=True, recursive=False):
        """ Remove local roles of specified members from an object.

        o 'obj' is the object on which to remove the role.

        o 'member_ids' is a sequence of user IDs from which to remove the role.

        o If 'reindex' is True, then reindex the security-related attributes
          of the object and all subobjects.

        o if 'recursive' is True, recurse over all subobjects of 'object'.

        o Raise Unauthorized if the currently-authenticated member cannot
          assign 'member_role' on 'obj'.

        Permission:  Public
        """

    def addMember(id, password, roles, domains):
        """ Adds a new member to the user folder.

        o Security checks will have already been performed. Called by
          the registration tool.

        Permission:  Private (Python only)
        """

    def deleteMembers(member_ids, delete_memberareas=1, delete_localroles=1):
        """ Remove specified members from the site.

        o Returns a sequence of member_ids of members actually deleted.

        o Remove the members from the user folder.

        o 'member_ids' is a sequence of one or more user IDs to remove.

        o Remove corresponding member data in the memberdata tool.

        o If 'delete_memberareas' is True, delete members' home folders
          including all content items.

        o If 'delete_localroles' is true, recursively delete members' local
          roles, starting from the site root.

        o Permission:  Manage users
        """

    def getPortalRoles():
        """ Return a sequence of role names defined by the portal itself.

        o Returned role names are those understood by the portal object.

        o Permission:  Manage portal
        """

    def setRoleMapping(portal_role, userfolder_role):
        """ Register a mapping of a role defined by the portal to a role
            coming from outside user sources.

        o Permission:  Manage portal
        """

    def getMappedRole(portal_role):
        """ Returns a mapped role name corresponding to 'portal_role', or
            the empty string if no mapping exists.

        o Mappings are defined via 'setRoleMapping'.

        o Permission:  Manage portal
        """

    def getMemberareaCreationFlag():
        """ Return True if the membership tool will create a member area for
            a user at login.

        o Permission:  Manage portal
        """

    def setMemberareaCreationFlag():
        """ Toggle the policy flag for create a member areas at login.

        o XXX:  Toggle is a weak semantic here;  shouldn't we be passing
                the value we want the flag to have?

        o Permission:  Manage portal
        """

    def createMemberArea(member_id=''):
        """ Return a member area for the given member, creating if necessary.

        o If member area creation is disabled, return None.

        o 'member_id', if passed, is the ID of the member whose folder is
          to be created;  if not passed, default to the authenticated member.

        o Permission:  Public # XXX?
        """

    def deleteMemberArea(member_id):
        """ Delete member area of specified member

        o Return True if a member area previously existed for the member.

        o 'member_id' identifies the member whose member is to be removed.

        o Permission:  Manage users
        """


#
#   Metadata tool interface
#
class IMetadataTool(Interface):

    """ CMF metadata policies interface.
    """

    id = Attribute('id',
            """ The tool's ID.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IMetadataTool)'.

            o Must be set to 'portal_metadata'.
            """)

    #
    #   Site-wide queries.
    #
    def getFullName(userid):
        """ Convert an internal userid to a "formal" name, if possible

        o 'userid' is the ID of the user within the user folder.

        o Used to map userid's for Creator, Contributor DCMI queries.
        """

    def getPublisher():
        """ Return the "formal" name of the publisher of the site.
        """

    #
    #   Content-specific queries.
    #
    def listAllowedSubjects(content=None):
        """ List the allowed values of the 'Subject' DCMI element.

        o If 'content' is not None, return only values appropriate for
          content's type;  otherwise, return "default" values.

        o 'Subject' elements should be keywords categorizing their resource.
        """

    def listAllowedFormats(content=None):
        """ List the allowed values of the 'Format' DCMI element.

        o If 'content' is not None, return only values appropriate for
          content's type;  otherwise, return "default" values.

        o 'Format' elements should be usable as HTTP 'Content-type' values.
        """

    def listAllowedLanguages(content=None):
        """ List the allowed values of the 'Language' DCMI element.

        o If 'content' is not None, return only values appropriate for
          content's type;  otherwise, return "default" values.

        o 'Language' element values should be suitable for generating
          HTTP headers.
        """

    def listAllowedRights(content=None):
        """ List the allowed values of the 'Rights' DCMI element.

        o If 'content' is not None, return only values appropriate for
          content's type;  otherwise, return "default" values.

        o The 'Rights' element describes copyright or other IP
          declarations pertaining to a resource.
        """

    #
    #   Validation policy hooks.
    #
    def setInitialMetadata(content):
        """ Set default initial values for content metatdata.
        """

    def validateMetadata(content):
        """ Enforce portal-wide policies about DCMI elements.

        o Such policy may, e.g., require non-empty title/description, etc.

        o Called by the CMF immediately before saving changes to the
          metadata of an object.

        o XXX:  Note that the default skins / edit methods do *not*
          call this method;  the choice of when to apply the validation
          is policy.
        """


#
#   Site Properties tool interface
#
class IPropertiesTool(Interface):

    """ Manage properties of the site as a whole.
    """

    id = Attribute('id',
            """ The tool's ID.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IPropertiesTool)'.

            o Must be set to 'portal_properties'.
            """)

    def editProperties(props):
        """ Change portal settings.

        o 'props' is a mapping of values to be updates.

        o Permission:  Manage portal
        """

    def title():
        """ Return the site's title.
        """

    def smtp_server():
        """ Return the configured SMTP server for the site.
        """


#
#   Registration tool interface
#
class IRegistrationTool(Interface):

    """ Manage policies for member registration.

    o Depends on IMembershipTool component.

    o Is not aware of membership storage details.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IRegistrationTool)'.

            o Must be set to "portal_registration"
            """,
            )

    def isRegistrationAllowed(REQUEST):
        """ Return True if the current user is allowed to add a member to
            the site, else False.

        o Permission:  Public
        """

    def testPasswordValidity(password, confirm=None):
        """ Return None if the password is valid;  otherwise return a string
            explaining why not.

        o 'password' is the candidate password string.

        o If 'confirm' is passed, XXX?

        o Permission:  Public
        """

    def testPropertiesValidity(new_properties, member=None):
        """ Return None if the supplied properties are valid;  otherwise
            return a string explaining why not.

        o 'new_properties' is a mapping containing the properties to test.

        o 'member', if passed, is the ID of the member for whome the
          properties are being set;  if not passed, use the currently-
          authenticated member.

        o Permission:  Public
        """

    def generatePassword():
        """ Return a generated password which is complies with the site's
            password policy.

        o Permission:  Public
        """

    def addMember(id, password, roles=('Member',), domains='',
                  properties=None):
        """ Creates and return a new member.

        o 'id' is the user ID of the member to be created;  raise ValueError
          if there already exists a member with the given 'id'.

        o 'password' is the user's password;  raise ValueError if the
          supplied 'password' does not comply with the site's password policy.

        o 'roles' is a list of roles to grant the new member;  raise
          Unauthorized if the currently-authenticated user is not
          allowed to grant one of the roles listed

          - "Member" is a special role that can always be granted

        o 'properties', if passed,  is a mapping with additional member
          properties;  raise ValueError if one or more properties do not
          comply with the site's policies.

        o Permission:  Add portal member
        """

    def isMemberIdAllowed(id):
        """ Return True if 'id' is not in use as a member ID and is not
            reserved, else False.

        o Permission:  Add portal member
        """

    def afterAdd(member, id, password, properties):
        """ Notification called by portal_registration.addMember() after a
            member has been added successfully.

        o Permission:  Private (Python only)
        """

    def mailPassword(forgotten_userid, REQUEST):
        """ Email a forgotten password to a member.

        o Raise ValueError if user ID is not found.

        o XXX: should probably *not* raise, in order to prevent cracking.

        o Permission:  Mail forgotten password
        """


#
#   Skins tool interfaces
#
class IDirectoryView(Interface):

    """ Directory views mount filesystem directories.
    """


class ISkinsContainer(Interface):

    """ An object that provides skins.
    """
    def getSkinPath(name):
        """ Convert a skin name to a skin path.

        o Permission:  Access contents information
        """

    def getDefaultSkin():
        """ Return the default skin name.

        o Permission:  Access contents information
        """

    def getRequestVarname():
        """ Return the variable name to look for in the REQUEST.

        o Permission:  Access contents information
        """

    def getSkinByPath(path, raise_exc=0):
        """ Return a skin at the given path.

        o XXX:  what are we doing here?

        o A skin path is a search path of layers of the format:
          'some/path, some/other/path, ...'.

        o Attributes are looked up in the layers in the named order.

        o A skin is a specially wrapped object that looks through the layers
          in the correct order.

        o Permission:  Private (Python only)
        """

    def getSkinByName(name):
        """ Get the named skin.

        Permission:  Private (Python only)
        """


class ISkinsTool(ISkinsContainer):

    """ An object that provides skins to a portal object.

    O XXX:  This shouldn't derive from ISkinsContainer?
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(ISkinsTool)'.

            o Must be set to "portal_skind"
            """,
            )

    def getSkinSelections():
        """ Get the sorted list of available skin names.

        o Permission:  Public
        """


#
#   Types tool interfaces
#
class ITypeInformation(Interface):

    """ Type definition interface.
    """

    def Metatype():
        """ Return the Zope 'meta_type' for this content object.

        o Deprecated (not all objects of a given type may even share
          the same meta_type).
        """

    def Title():
        """ Return the "human readable" type name

        o Note that it may not map exactly to the 'meta_type', e.g.,
          for l10n/i18n or where a single content class is being
          used twice, under different names.
        """

    def Description():
        """ Return a textual description of the type

        o This descriptoin is used for display in a "constructor list".
        """

    def isConstructionAllowed(container):
        """ Return True if the current user is allowed to construct an
            instance of this type in 'container, else False.
        """

    def allowType(contentType):
        """ Can objects of 'contentType' be added to containers of our type?
        """

    def constructInstance(container, id):
        """ Build a "bare" instance of the appropriate type in 'container'.

        o Give the new instance an ID of 'id'.

        o Return the newly-created instance, seated in 'container'.
        """

    def allowDiscussion():
        """ Return True if objects of this type are allowed to support
            discussion, else False.

        o Individual objects may still disable discussion.
        """

    def getIcon():
        """ Return the portal-relative URL for the icon for this type.
        """

    def getMethodAliases():
        """ Return a mapping of method aliases for this type.

        o XXX:  define keys and values of the mapping.

        o Permission:  Manage portal
        """

    def setMethodAliases(aliases):
        """ Assign method aliases for this type.

        o Return True if the operation changed any aliases, else False.

        o 'aliases' is the mapping of aliases to be assigned.

        o XXX:  define keys and values of the mapping.

        o Permission:  Manage portal
        """

    def queryMethodID(alias, default=None, context=None):
        """ Return the method ID for a given alias.

        o 'context', if passed, points to the object calling this method.
           It may be used to return dynamic values based on the caller.
           XXX:  this is unclear

        o 'default' is returned if no such alias is defined.

        o Permission:  Public

        Returns:  Method ID or default value
        """


class ITypesTool(Interface):

    """ Register content types for the site.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(ITypesTool)'.

            o Must be set to "portal_types"
            """,
            )

    def getTypeInfo(contentType):
        """ Return an ITypeInformation for the given type name / object.

        o If 'contentType' is actually an object, rather than a string,
          attempt to look up the appropriate type info using its 'portal_type'.

        o Permission:  Public
        """

    def listTypeInfo(container=None):
        """ Return a sequence of ITypeInformations registered for the
            site.

        o If 'container' is passed, filter the list according to the user's
          permissions to add content in that place.

        o Permission:  Public
        """

    def listContentTypes(container=None, by_metatype=0):
        """ Return a sequence of IDs of ITypeInformations registered
            for the site.

        o If 'by_metatype' is True, return meta_types instead (this variant
          is deprecated).

        o If 'container' is passed, filter the list according to the user's
          permissions to add content in that place.

        o Permission:  Public
        """

    def constructContent(contentType, container, id, RESPONSE=None,
                         *args, **kw):
        """ Build an instance of the appropriate type in 'container'

        o 'contentType' is the name of the ITypeInformation to be
          constructed.

        o Assign the instance the given 'id', if possible.

        o If 'RESPONSE' is passed, redirect to the new object's
          "initial view";  otherwise return the new object's 'id' (which
          may have morphed during construction).

        o Raise Unauthorized if the current user is not allowed to construct
          items of the given type in 'container'.
        """


#
#   Undo tool interface
#
class IUndoTool(Interface):

    """ Provide access to Zope undo functions.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IUndoTool)'.

            o Must be set to "portal_undo"
            """,
            )

    def listUndoableTransactionsFor(object,
                                    first_transaction=None,
                                    last_transaction=None,
                                    PrincipiaUndoBatchSize=None):
        """ List all transaction IDs the user is allowed to undo on 'object'.

        o Return a list of "transaction info" objects, using the given
          parameters to batch the results.

        o XXX:  this needs documentation / testing.

        o Permission:  Undo changes
        """

    def undo(object, transaction_info):
        """Performs an undo operation.

        o Permission:  Undo changes
        """


#
#   URL tool interface
#
class IURLTool(Interface):

    """ CMF URL Tool interface.

    This interface provides a common mechanism for finding the 'root'
    object of a CMFSite, and for computing paths to objects relative to
    that root.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IURLTool)'.

            o Must be set to "portal_url"
            """,
            )

    def __call__(relative=0, *args, **kw):
        """ Return URL of the site, as a string.

        o If 'relative' is True, return only the "path" portion of the site
          object's URL; otherwise, return the absolute URL

        o In either case, the returned path respects virtual hosting.

        o The site is the parent of the tool.

        o Permission:  Public
        """

    def getPortalObject():
        """ Return the site object itself.

        o The site is the parent of the tool.

        o Permission:  Public
        """

    def getRelativeContentPath(content):
        """ Return the site-relative path for 'content'

        o The site is the parent of the tool.

        o Return a sequence of path elements.

        o Permission:  Public
        """

    def getRelativeContentURL(content):
        """ Return the site-relative URL for 'content', as a string.

        o The site is the parent of the tool.

        o This is helpful for virtual hosting situations.

        o Same method as 'getRelativeURL()'

        o Permission:  Public
        """

    def getRelativeUrl(content):
        """ Return the site-relative URL for 'content', as a string.

        o The site is the parent of the tool.

        o This is helpful for virtual hosting situations.

        o Same method as 'getRelativeContentURL()'

        o Permission:  Public
        """

    def getPortalPath():
        """ Return the portal object's URL without the server URL component.

        o Return a slash-delimited string.

        o Permission:  Public
        """


#
#   Workflow tool interfaces
#
class IWorkflowTool(Interface):

    """This tool accesses and changes the workflow state of content.
    """

    id = Attribute('id',
            """ The ID of the tool.

            o BBB:  for use in 'getToolByName';  in the future, prefer
              'zapi.getUtility(IWorkflowTool)'.

            o Must be set to "portal_workflow"
            """,
            )

    def getCatalogVariablesFor(ob):
        """ Return a mapping of "workflow-relevant" attributes.

        o Invoked by 'portal_catalog' when indexing content.

        o Allows workflows to add variables to the catalog based on workflow
          status, making it possible to implement queues.

        o Permission:  Private (Python only)
        """

    def getActionsFor(ob):
        """ Return a list of action dictionaries for 'ob'

        o Generate the list as though queried via
          'ActionsTool.listFilteredActionsFor'.

        o This method is deprecated and will be removed in CMF 1.7.

        o Permission:  Public
        """

    def doActionFor(ob, action, wf_id=None, *args, **kw):
        """ Perform the given workflow action on 'ob'.

        o 'ob' is the target object.

        o 'action' is the ID of the action to perform.

        o 'wf_id', if passed, is the ID of the workflow supplying the action.

        o 'args' and 'kw', if passed, are applied to the invoked action.

        o Invoked by user interface code, allowing the user to request a
          workflow action.

        o The workflow object must perform its own security checks.

        o Permission:  Public
        """

    def getInfoFor(ob, name, default=_marker, wf_id=None):
        """ Return the given bit of workflow information for the object.

        o 'ob' is the target object.

        o 'name' is the name of the information requested.

        o 'default', if passed, will be returned if 'name' is not found;
          if 'default' is not passed, then raise ValueError.

        o 'wf_id', if passed, is the ID of the workflow supplying the action.

        o Invoked by user interface code, allowing the user to request
          information provided by the workflow.

        o The workflow object must perform its own security checks.

        o Permission:  Public
        """

    def notifyCreated(ob):
        """ Notify all applicable workflows that an object has been created.

        o 'ob' is the newly-created object;  it will already be "seated"
          in its new place.

        o Permission:  Private (Python only)
        """

    def notifyBefore(ob, action):
        """ Notify all applicable workflows of an action before it happens.

        o 'ob' is the content object which is the target of the action.

        o 'action' usually corresponds to a method name.

        o Participating workflows may veto the action by raising
          WorkflowException.

        o Unless vetoed, the tool will later call either a 'notifySuccess' or
          'notifyException'

        o Permission:  Private (Python only)
        """

    def notifySuccess(ob, action, result=None):
        """ Notify all applicable workflows that an action has taken place.

        o 'ob' is the content object which is the target of the action.

        o 'action' usually corresponds to a method name.

        o 'result' is the value returned from the action.

        o Permission:  Private (Python only)
        """

    def notifyException(ob, action, exc):
        """ Notify all applicable workflows that an action failed.

        o 'ob' is the content object which is the target of the action.

        o 'action' usually corresponds to a method name.

        o 'exc' is the 'sys.exec_info' triple for the exception.

        o Permission:  Private (Python only)
        """

    def getHistoryOf(wf_id, ob):
        """ Returns the history of an object for a given workflow.

        o 'wf_id' is the id of the selected workflow.

        o 'ob' is the content object.

        o Invoked by workflow definitions.

        o Permission:  Private (Python only)
        """

    def getStatusOf(wf_id, ob):
        """ Return the last element of a workflow history for a given workflow.

        o 'wf_id' is the id of the selected workflow.

        o 'ob' is the content object.

        o Invoked by workflow definitions.

        o Permission:  Private (Python only)
        """

    def setStatusOf(wf_id, ob, status):
        """ Append a record to the workflow history of a given workflow.

        o 'wf_id' is the id of the selected workflow.

        o 'ob' is the content object.

        o 'status' is a mapping defining the history item to append.

        o Invoked by workflow definitions.

        o Permission:  Private (Python only)
        """


class IWorkflowDefinition(Interface):

    """Plugin interface for workflow definitions managed by IWorkflowTool.
    """

    def getCatalogVariablesFor(ob):
        """ Return a mapping of attributes relevant to this workflow.

        o Invoked by the workflow tool.

        o Allows workflows to add variables to the catalog based on workflow
          status, making it possible to implement queues.

        o Permission:  Private (Python only)
        """

    def updateRoleMappingsFor(ob):
        """ Update the object permissions according to the current workflow
            state of 'ob'.

        o Note that having the same permission(s) controlled by more than one
          workflow defintiion for an object results in undefined behavior.

        o Permission:  Private (Python only)
        """

    def listObjectActions(info):
        """ Return a sequence of IActionInformation defining workflow actions.

        o 'info' is an ObjectActionInformation structure. XXX?

        o Returned actions are relevant to 'info.content' (this method is
          called only when this workflow is applicable to 'info.content').

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def listGlobalActions(info):
        """ Return a sequence of IActionInformation defining workflow actions.

        o 'info' is an ObjectActionInformation structure. XXX?

        o Returned actions are "global", i.e. relevant to the user and  the
          site, rather than to any particular content object (this method is
          generally called on every request!)

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def isActionSupported(ob, action, **kw):
        """ Return True if the given workflow action is supported by this
            workfow for a content object, else False.

        o 'ob' is the content object.

        o 'action' is the ID of the requested workflow action.

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def doActionFor(ob, action, comment=''):
        """ Perform the requested workflow action on a content object.

        o 'ob' is the content object.

        o 'action' is the ID of the requested workflow action.

        o 'comment' is passed to the method corresponding to 'action'.

        o Invoked by the portal_workflow tool.

        o Allows the user to request a workflow action.

        o This method must perform its own security checks.

        o Permission:  Private (Python only)
        """

    def isInfoSupported(ob, name):
        """ Return True if the given info name is supported by this workflow
            for a given content object, else False.

        o 'ob' is the content object.

        o 'name' is the name of the requested workflow information.

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def getInfoFor(ob, name, default):
        """ Return the requested workflow information for a content object.

        o 'ob' is the content object.

        o 'name' is the name of the requested workflow information.

        o 'default' is returned if 'name' is not found.

        o Invoked by the portal_workflow tool.

        o This method must perform its own security checks.

        o Permission:  Private (Python only)
        """

    def notifyCreated(ob):
        """ Notification that an object has been created and put in its place.

        o 'ob' is the newly-created object.

        o Invoked by the portal_workflow tool.

        o The workflow may set initial workflow state, etc. for the new
          object.

        o Permission:  Private (Python only)
        """

    def notifyBefore(ob, action):
        """ Notification of a workflow action before it happens.

        o 'ob' is the target object of the action.

        o 'action' is a string identifying the impending action;
          usually it corresponds to a method name.

        o This workflow may veto by raising WorkflowException.

        o Unless some workflow raises WorkflowException is thrown,
          the workflow tool will emit either 'notifySuccess' or
          'notifyException' after the action.

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def notifySuccess(ob, action, result):
        """ Notification that a workflow action has taken place.

        o 'ob' is the target object of the action.

        o 'action' is a string identifying the succesful action;
          usually it corresponds to a method name.

        o 'result' is the return value from the method called.

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """

    def notifyException(ob, action, exc):
        """ Notifies this workflow that an action failed.

        o 'ob' is the target object of the action.

        o 'action' is a string identifying the failed action;
          usually it corresponds to a method name.

        o 'exc' is the 'sys.exc_info' triple for the exception.

        o Invoked by the portal_workflow tool.

        o Permission:  Private (Python only)
        """
