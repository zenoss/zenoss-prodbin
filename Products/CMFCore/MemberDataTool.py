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
""" Basic member data tool.

$Id: MemberDataTool.py 38513 2005-09-19 12:01:33Z jens $
"""

from AccessControl import ClassSecurityInfo
from Acquisition import aq_inner, aq_parent, aq_base
from BTrees.OOBTree import OOBTree
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.PropertyManager import PropertyManager
from OFS.SimpleItem import SimpleItem
from ZPublisher.Converters import type_converters

from ActionProviderBase import ActionProviderBase
from exceptions import BadRequest
from interfaces.portal_memberdata import MemberData as IMemberData
from interfaces.portal_memberdata import portal_memberdata as IMemberDataTool
from permissions import ManagePortal
from permissions import SetOwnProperties
from permissions import ViewManagementScreens
from utils import _dtmldir
from utils import getToolByName
from utils import UniqueObject


_marker = []  # Create a new marker object.


class MemberDataTool (UniqueObject, SimpleItem, PropertyManager, ActionProviderBase):
    """ This tool wraps user objects, making them act as Member objects.
    """

    __implements__ = (IMemberDataTool, ActionProviderBase.__implements__)

    id = 'portal_memberdata'
    meta_type = 'CMF Member Data Tool'
    _actions = ()

    _v_temps = None
    _properties = ()

    security = ClassSecurityInfo()

    manage_options=( ActionProviderBase.manage_options +
                     ({ 'label' : 'Overview'
                       , 'action' : 'manage_overview'
                       }
                     , { 'label' : 'Contents'
                       , 'action' : 'manage_showContents'
                       }
                     )
                   + PropertyManager.manage_options
                   + SimpleItem.manage_options
                   )

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainMemberDataTool', _dtmldir )

    security.declareProtected(ViewManagementScreens, 'manage_showContents')
    manage_showContents = DTMLFile('memberdataContents', _dtmldir )


    def __init__(self):
        self._members = OOBTree()
        # Create the default properties.
        self._setProperty('email', '', 'string')
        self._setProperty('portal_skin', '', 'string')
        self._setProperty('listed', '', 'boolean')
        self._setProperty('login_time', '2000/01/01', 'date')
        self._setProperty('last_login_time', '2000/01/01', 'date')

    #
    #   'portal_memberdata' interface methods
    #
    security.declarePrivate('getMemberDataContents')
    def getMemberDataContents(self):
        '''
        Return the number of members stored in the _members
        BTree and some other useful info
        '''
        membertool   = getToolByName(self, 'portal_membership')
        members      = self._members
        user_list    = membertool.listMemberIds()
        member_list  = members.keys()
        member_count = len(members)
        orphan_count = 0

        for member in member_list:
            if member not in user_list:
                orphan_count = orphan_count + 1

        return [{ 'member_count' : member_count,
                  'orphan_count' : orphan_count }]

    security.declarePrivate('searchMemberData')
    def searchMemberData(self, search_param, search_term, attributes=()):
        """ Search members. """
        res = []

        if not search_param:
            return res

        membership = getToolByName(self, 'portal_membership')

        if len(attributes) == 0:
            attributes = ('id', 'email')

        if search_param == 'username':
            search_param = 'id'

        for user_id in self._members.keys():
            u = membership.getMemberById(user_id)

            if u is not None:
                memberProperty = u.getProperty
                searched = memberProperty(search_param, None)

                if searched is not None and searched.find(search_term) != -1:
                    user_data = {}

                    for desired in attributes:
                        if desired == 'id':
                            user_data['username'] = memberProperty(desired, '')
                        else:
                            user_data[desired] = memberProperty(desired, '')

                    res.append(user_data)

        return res

    security.declarePrivate( 'searchMemberDataContents' )
    def searchMemberDataContents( self, search_param, search_term ):
        """ Search members. This method will be deprecated soon. """
        res = []

        if search_param == 'username':
            search_param = 'id'

        mtool   = getToolByName(self, 'portal_membership')

        for member_id in self._members.keys():

            user_wrapper = mtool.getMemberById( member_id )

            if user_wrapper is not None:
                memberProperty = user_wrapper.getProperty
                searched = memberProperty( search_param, None )

                if searched is not None and searched.find(search_term) != -1:

                    res.append( { 'username': memberProperty( 'id' )
                                , 'email' : memberProperty( 'email', '' )
                                }
                            )
        return res

    security.declarePrivate('pruneMemberDataContents')
    def pruneMemberDataContents(self):
        """ Delete data contents of all members not listet in acl_users.
        """
        membertool= getToolByName(self, 'portal_membership')
        members = self._members
        user_list = membertool.listMemberIds()

        for member_id in list(members.keys()):
            if member_id not in user_list:
                del members[member_id]

    security.declarePrivate('wrapUser')
    def wrapUser(self, u):
        '''
        If possible, returns the Member object that corresponds
        to the given User object.
        '''
        id = u.getId()
        members = self._members
        if not members.has_key(id):
            # Get a temporary member that might be
            # registered later via registerMemberData().
            temps = self._v_temps
            if temps is not None and temps.has_key(id):
                m = temps[id]
            else:
                base = aq_base(self)
                m = MemberData(base, id)
                if temps is None:
                    self._v_temps = {id:m}
                    if hasattr(self, 'REQUEST'):
                        # No REQUEST during tests.
                        self.REQUEST._hold(CleanupTemp(self))
                else:
                    temps[id] = m
        else:
            m = members[id]
        # Return a wrapper with self as containment and
        # the user as context.
        return m.__of__(self).__of__(u)

    security.declarePrivate('registerMemberData')
    def registerMemberData(self, m, id):
        """ Add the given member data to the _members btree.
        """
        self._members[id] = aq_base(m)

    security.declarePrivate('deleteMemberData')
    def deleteMemberData(self, member_id):
        """ Delete member data of specified member.
        """
        members = self._members
        if members.has_key(member_id):
            del members[member_id]
            return 1
        else:
            return 0

InitializeClass(MemberDataTool)


class CleanupTemp:
    """Used to cleanup _v_temps at the end of the request."""
    def __init__(self, tool):
        self._tool = tool
    def __del__(self):
        try:
            del self._tool._v_temps
        except (AttributeError, KeyError):
            # The object has already been deactivated.
            pass


class MemberData (SimpleItem):

    __implements__ = IMemberData

    security = ClassSecurityInfo()

    def __init__(self, tool, id):
        self.id = id
        # Make a temporary reference to the tool.
        # The reference will be removed by notifyModified().
        self._tool = tool

    security.declarePrivate('notifyModified')
    def notifyModified(self):
        # Links self to parent for full persistence.
        tool = getattr(self, '_tool', None)
        if tool is not None:
            del self._tool
            tool.registerMemberData(self, self.getId())

    security.declarePublic('getUser')
    def getUser(self):
        # The user object is our context, but it's possible for
        # restricted code to strip context while retaining
        # containment.  Therefore we need a simple security check.
        parent = aq_parent(self)
        bcontext = aq_base(parent)
        bcontainer = aq_base(aq_parent(aq_inner(self)))
        if bcontext is bcontainer or not hasattr(bcontext, 'getUserName'):
            raise 'MemberDataError', "Can't find user data"
        # Return the user object, which is our context.
        return parent

    def getTool(self):
        return aq_parent(aq_inner(self))

    security.declarePublic('getMemberId')
    def getMemberId(self):
        return self.getUser().getId()

    security.declareProtected(SetOwnProperties, 'setProperties')
    def setProperties(self, properties=None, **kw):
        '''Allows the authenticated member to set his/her own properties.
        Accepts either keyword arguments or a mapping for the "properties"
        argument.
        '''
        if properties is None:
            properties = kw
        membership = getToolByName(self, 'portal_membership')
        registration = getToolByName(self, 'portal_registration', None)
        if not membership.isAnonymousUser():
            member = membership.getAuthenticatedMember()
            if registration:
                failMessage = registration.testPropertiesValidity(properties, member)
                if failMessage is not None:
                    raise BadRequest(failMessage)
            member.setMemberProperties(properties)
        else:
            raise BadRequest('Not logged in.')

    security.declarePrivate('setMemberProperties')
    def setMemberProperties(self, mapping):
        '''Sets the properties of the member.
        '''
        # Sets the properties given in the MemberDataTool.
        tool = self.getTool()
        for id in tool.propertyIds():
            if mapping.has_key(id):
                if not self.__class__.__dict__.has_key(id):
                    value = mapping[id]
                    if type(value)==type(''):
                        proptype = tool.getPropertyType(id) or 'string'
                        if type_converters.has_key(proptype):
                            value = type_converters[proptype](value)
                    setattr(self, id, value)
        # Hopefully we can later make notifyModified() implicit.
        self.notifyModified()

    # XXX: s.b., getPropertyForMember(member, id, default)?

    security.declarePublic('getProperty')
    def getProperty(self, id, default=_marker):

        tool = self.getTool()
        base = aq_base( self )

        # First, check the wrapper (w/o acquisition).
        value = getattr( base, id, _marker )
        if value is not _marker:
            return value

        # Then, check the tool and the user object for a value.
        tool_value = tool.getProperty( id, _marker )
        user_value = getattr( self.getUser(), id, _marker )

        # If the tool doesn't have the property, use user_value or default
        if tool_value is _marker:
            if user_value is not _marker:
                return user_value
            elif default is not _marker:
                return default
            else:
                raise ValueError, 'The property %s does not exist' % id

        # If the tool has an empty property and we have a user_value, use it
        if not tool_value and user_value is not _marker:
            return user_value

        # Otherwise return the tool value
        return tool_value

    security.declarePrivate('getPassword')
    def getPassword(self):
        """Return the password of the user."""
        return self.getUser()._getPassword()

    security.declarePrivate('setSecurityProfile')
    def setSecurityProfile(self, password=None, roles=None, domains=None):
        """Set the user's basic security profile"""
        u = self.getUser()

        # The Zope User API is stupid, it should check for None.
        if roles is None:
            roles = list(u.getRoles())
            if 'Authenticated' in roles:
                roles.remove('Authenticated')
        if domains is None:
            domains = u.getDomains()

        u.userFolderEditUser(u.getUserName(), password, roles, domains)

    def __str__(self):
        return self.getMemberId()

    ### User object interface ###

    security.declarePublic('getUserName')
    def getUserName(self):
        """Return the username of a user"""
        return self.getUser().getUserName()

    security.declarePublic('getId')
    def getId(self):
        """Get the ID of the user. The ID can be used, at least from
        Python, to get the user from the user's
        UserDatabase"""
        return self.getUser().getId()

    security.declarePublic('getRoles')
    def getRoles(self):
        """Return the list of roles assigned to a user."""
        return self.getUser().getRoles()

    security.declarePublic('getRolesInContext')
    def getRolesInContext(self, object):
        """Return the list of roles assigned to the user,
           including local roles assigned in context of
           the passed in object."""
        return self.getUser().getRolesInContext(object)

    security.declarePublic('getDomains')
    def getDomains(self):
        """Return the list of domain restrictions for a user"""
        return self.getUser().getDomains()

    security.declarePublic('has_role')
    def has_role(self, roles, object=None):
        """Check to see if a user has a given role or roles."""
        return self.getUser().has_role(roles, object)

    # There are other parts of the interface but they are
    # deprecated for use with CMF applications.

InitializeClass(MemberData)
