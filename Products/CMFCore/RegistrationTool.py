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
""" Basic user registration tool.

$Id: RegistrationTool.py 36633 2004-10-29 14:37:36Z jens $
"""

import re

from Globals import InitializeClass
from Globals import DTMLFile
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from random import choice

from ActionProviderBase import ActionProviderBase
from permissions import AddPortalMember
from permissions import MailForgottenPassword
from permissions import ManagePortal
from utils import UniqueObject
from utils import _checkPermission
from utils import _limitGrantedRoles
from utils import getToolByName
from utils import _dtmldir

from interfaces.portal_registration \
        import portal_registration as IRegistrationTool


class RegistrationTool(UniqueObject, SimpleItem, ActionProviderBase):

    """ Create and modify users by making calls to portal_membership.
    """

    __implements__ = (IRegistrationTool, ActionProviderBase.__implements__)

    id = 'portal_registration'
    meta_type = 'CMF Registration Tool'
    member_id_pattern = ''
    default_member_id_pattern = "^[A-Za-z][A-Za-z0-9_]*$"
    _ALLOWED_MEMBER_ID_PATTERN = re.compile(default_member_id_pattern)

    security = ClassSecurityInfo()

    manage_options = (ActionProviderBase.manage_options +
                     ({ 'label' : 'Overview', 'action' : 'manage_overview' }
                     ,{ 'label' : 'Configure', 'action' : 'manage_configuration' } 
                     ) + SimpleItem.manage_options)

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainRegistrationTool', _dtmldir )

    security.declareProtected(ManagePortal, 'manage_configuration')
    manage_configuration = DTMLFile('configureRegistrationTool', _dtmldir)

    security.declareProtected(ManagePortal, 'manage_editIDPattern')
    def manage_editIDPattern(self, pattern, REQUEST=None):
        """Edit the allowable member ID pattern TTW"""
        pattern.strip()

        if len(pattern) > 0:
            self.member_id_pattern = pattern
            self._ALLOWED_MEMBER_ID_PATTERN = re.compile(pattern)
        else:
            self.member_id_pattern = ''
            self._ALLOWED_MEMBER_ID_PATTERN = re.compile(
                                                self.default_member_id_pattern)

        if REQUEST is not None:
            msg = 'Member ID Pattern changed'
            return self.manage_configuration(manage_tabs_message=msg)

    security.declareProtected(ManagePortal, 'getIDPattern')
    def getIDPattern(self):
        """ Return the currently-used member ID pattern """
        return self.member_id_pattern

    security.declareProtected(ManagePortal, 'getDefaultIDPattern')
    def getDefaultIDPattern(self):
        """ Return the currently-used member ID pattern """
        return self.default_member_id_pattern


    #
    #   'portal_registration' interface methods
    #
    security.declarePublic('isRegistrationAllowed')
    def isRegistrationAllowed(self, REQUEST):
        '''Returns a boolean value indicating whether the user
        is allowed to add a member to the portal.
        '''
        return _checkPermission(AddPortalMember, self.aq_inner.aq_parent)

    security.declarePublic('testPasswordValidity')
    def testPasswordValidity(self, password, confirm=None):
        '''If the password is valid, returns None.  If not, returns
        a string explaining why.
        '''
        return None

    security.declarePublic('testPropertiesValidity')
    def testPropertiesValidity(self, new_properties, member=None):
        '''If the properties are valid, returns None.  If not, returns
        a string explaining why.
        '''
        return None

    security.declarePublic('generatePassword')
    def generatePassword(self):
        """ Generate a valid password.
        """
        # we don't use these to avoid typos: OQ0Il1
        chars = 'ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join( [ choice(chars) for i in range(6) ] )

    security.declareProtected(AddPortalMember, 'addMember')
    def addMember(self, id, password, roles=('Member',), domains='',
                  properties=None):
        '''Creates a PortalMember and returns it. The properties argument
        can be a mapping with additional member properties. Raises an
        exception if the given id already exists, the password does not
        comply with the policy in effect, or the authenticated user is not
        allowed to grant one of the roles listed (where Member is a special
        role that can always be granted); these conditions should be
        detected before the fact so that a cleaner message can be printed.
        '''
        if not self.isMemberIdAllowed(id):
            raise ValueError('The login name you selected is already '
                             'in use or is not valid. Please choose another.')

        failMessage = self.testPasswordValidity(password)
        if failMessage is not None:
            raise ValueError(failMessage)

        if properties is not None:
            failMessage = self.testPropertiesValidity(properties)
            if failMessage is not None:
                raise ValueError(failMessage)

        # Limit the granted roles.
        # Anyone is always allowed to grant the 'Member' role.
        _limitGrantedRoles(roles, self, ('Member',))

        membership = getToolByName(self, 'portal_membership')
        membership.addMember(id, password, roles, domains, properties)

        member = membership.getMemberById(id)
        self.afterAdd(member, id, password, properties)
        return member

    security.declareProtected(AddPortalMember, 'isMemberIdAllowed')
    def isMemberIdAllowed(self, id):
        '''Returns 1 if the ID is not in use and is not reserved.
        '''
        if len(id) < 1 or id == 'Anonymous User':
            return 0
        if not self._ALLOWED_MEMBER_ID_PATTERN.match( id ):
            return 0
        membership = getToolByName(self, 'portal_membership')
        if membership.getMemberById(id) is not None:
            return 0
        return 1

    security.declarePublic('afterAdd')
    def afterAdd(self, member, id, password, properties):
        '''Called by portal_registration.addMember()
        after a member has been added successfully.'''
        pass

    security.declareProtected(MailForgottenPassword, 'mailPassword')
    def mailPassword(self, forgotten_userid, REQUEST):
        '''Email a forgotten password to a member.  Raises an exception
        if user ID is not found.
        '''
        raise NotImplementedError

InitializeClass(RegistrationTool)
