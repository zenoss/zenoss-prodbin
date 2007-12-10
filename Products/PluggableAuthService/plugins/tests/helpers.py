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
from Products.PluggableAuthService.tests.test_PluggableAuthService \
    import FauxContainer

class FauxPAS( FauxContainer ):

    def __init__( self ):
        self._id = 'acl_users'

    def searchPrincipals( self, **kw ):
        id = kw.get( 'id' )
        return [ { 'id': id } ]

class FauxSmartPAS( FauxContainer ):

    def __init__( self ):
        self._id = 'acl_users'
        self.user_ids = {}

    def searchPrincipals( self, **kw ):
        id = kw.get( 'id' )
        prin = self.user_ids.get(id, None)
        return (prin and [ { 'id': id } ]) or []

class DummyUser:

    def __init__( self, id, groups=() ):
        self._id = id
        self._groups = groups

    def getId( self ):
        return self._id

    def getGroups( self ):
        return self._groups

