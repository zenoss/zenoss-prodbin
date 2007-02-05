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
""" Registration tool interface.

$Id: portal_registration.py 36457 2004-08-12 15:07:44Z jens $
"""

from Interface import Attribute
from Interface import Interface


class portal_registration(Interface):
    '''Establishes policies for member registration. Depends on
    portal_membership. Is not aware of membership storage details.
    '''
    id = Attribute('id', 'Must be set to "portal_registration"')

    #isRegistrationAllowed__roles__ = None  # Anonymous permission
    def isRegistrationAllowed(REQUEST):
        '''Returns a boolean value indicating whether the user
        is allowed to add a member to the portal.
        '''

    #testPasswordValidity__roles__ = None  # Anonymous permission
    def testPasswordValidity(password, confirm=None):
        '''If the password is valid, returns None.  If not, returns
        a string explaining why.
        '''

    #testPropertiesValidity__roles__ = None  # Anonymous permission
    def testPropertiesValidity(new_properties, member=None):
        '''If the properties are valid, returns None.  If not, returns
        a string explaining why.
        '''

    #generatePassword__roles__ = None  # Anonymous permission
    def generatePassword():
        '''Generates a password which is guaranteed to comply
        with the password policy.
        '''

    # permission: 'Add portal member'
    def addMember(id, password, roles=('Member',), domains='',
                  properties=None):
        '''Creates a PortalMember and returns it. The properties argument
        can be a mapping with additional member properties. Raises an
        exception if the given id already exists, the password does not
        comply with the policy in effect, or the authenticated user is not
        allowed to grant one of the roles listed (where Member is a special
        role that can always be granted); these conditions should be
        detected before the fact so that a cleaner message can be printed.
        '''

    # permission: 'Add portal member'
    def isMemberIdAllowed(id):
        '''Returns 1 if the ID is not in use and is not reserved.
        '''

    #afterAdd__roles__ = ()  # No permission.
    def afterAdd(member, id, password, properties):
        '''Called by portal_registration.addMember()
        after a member has been added successfully.'''

    # permission: 'Mail forgotten password'
    def mailPassword(forgotten_userid, REQUEST):
        '''Email a forgotten password to a member.  Raises an exception
        if user ID is not found.
        '''
