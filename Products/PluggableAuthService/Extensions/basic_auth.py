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
""" Basic auth helpers.

$Id: basic_auth.py 39144 2004-08-12 15:15:55Z jens $
"""

def extraction( self, request ):

    """ Fetch HTTP Basic Auth credentials from the request.
    """
    creds = request._authUserPW()

    if creds is not None:
        name, password = creds

        return { 'login' : name, 'password' : password }

    return {}

def authentication( self, credentials ):

    """ Authenticate against nested acl_users.
    """
    real_user_folder = self.simple_uf.acl_users

    login = credentials.get( 'login' )
    password = credentials.get( 'password' )

    user = real_user_folder.authenticate( login, password, {} )

    return user is not None and login or None


def authorize( self, user ):

    """ Fetch user roles from nested acl_users.
    """
    real_user_folder = self.simple_uf.acl_users
    real_user = real_user_folder.getUserById( user.getId() )
    return real_user.getRoles()
