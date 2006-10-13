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
import unittest

from Products.PluggableAuthService.tests.conformance \
    import IRolesPlugin_conformance
from Products.PluggableAuthService.tests.conformance \
    import IRoleEnumerationPlugin_conformance
from Products.PluggableAuthService.tests.conformance \
    import IRoleAssignerPlugin_conformance

from Products.PluggableAuthService.plugins.tests.helpers \
     import FauxPAS, FauxSmartPAS, DummyUser

class ZODBRoleManagerTests( unittest.TestCase
                          , IRolesPlugin_conformance
                          , IRoleEnumerationPlugin_conformance
                          , IRoleAssignerPlugin_conformance
                          ):

    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.ZODBRoleManager \
            import ZODBRoleManager

        return ZODBRoleManager

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id=id, *args, **kw )

    def test_empty( self ):

        zrm = self._makeOne()

        self.assertEqual( len( zrm.listRoleIds() ), 0 )
        self.assertEqual( len( zrm.enumerateRoles() ), 0 )

        user = DummyUser( 'userid' )
        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 0 )

    def test_addRole( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne().__of__( root )

        zrm.addRole( 'roleid', 'Role', 'This is a role' )

        role_ids = zrm.listRoleIds()
        self.assertEqual( len( role_ids ), 1 )
        self.assertEqual( role_ids[0], 'roleid' )

        info_list = zrm.enumerateRoles()
        self.assertEqual( len( info_list ), 1 )
        info = info_list[ 0 ]
        self.assertEqual( info[ 'id' ], 'roleid' )

    def test_addRole_duplicate_check( self ):

        zrm = self._makeOne()

        zrm.addRole( 'roleid', 'Role', 'This is a role' )

        self.assertRaises( KeyError, zrm.addRole
                         , 'roleid', 'Alias', 'duplicate' )

    def test_removeRole_nonesuch( self ):

        zrm = self._makeOne()

        self.assertRaises( KeyError, zrm.removeRole, 'nonesuch' )

    def test_removeRole_valid_id( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne().__of__( root )

        zrm.addRole( 'roleid', 'Role', 'This is a role' )
        zrm.addRole( 'doomed', 'Fatal', 'rust never sleeps' )

        zrm.removeRole( 'doomed' )

        role_ids = zrm.listRoleIds()
        self.assertEqual( len( role_ids ), 1 )
        self.assertEqual( len( zrm.enumerateRoles() ), 1 )
        self.assertEqual( role_ids[0], 'roleid' )

    def test_enumerateRoles_no_criteria( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='no_crit' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zrm.addRole( id, 'Role %s' % id, 'This is role, %s' % id )

        info_list = zrm.enumerateRoles()

        self.assertEqual( len( info_list ), len( ID_LIST ) )

        sorted = list( ID_LIST )
        sorted.sort()

        for i in range( len( sorted ) ):

            self.assertEqual( info_list[ i ][ 'id' ], sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'pluginid' ], 'no_crit' )
            self.assertEqual( info_list[ i ][ 'properties_url' ]
                            , 'no_crit/manage_roles?role_id=%s' % sorted[ i ])
            self.assertEqual( info_list[ i ][ 'members_url' ]
                            , 'no_crit/manage_roles?role_id=%s&assign=1'
                                % sorted[ i ])

    def test_enumerateRoles_exact( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='exact' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zrm.addRole( id, 'Role %s' % id, 'This is role, %s' % id )

        info_list = zrm.enumerateRoles( id='bar', exact_match=True )

        self.assertEqual( len( info_list ), 1 )
        info = info_list[ 0 ]

        self.assertEqual( info[ 'id' ], 'bar' )
        self.assertEqual( info[ 'pluginid' ], 'exact' )
        self.assertEqual( info[ 'properties_url' ]
                        , 'exact/manage_roles?role_id=bar' )
        self.assertEqual( info[ 'members_url' ]
                        , 'exact/manage_roles?role_id=bar&assign=1' )
        self.assertEqual( info[ 'title' ], 'Role bar' )
        self.assertEqual( info[ 'description' ], 'This is role, bar' )


    def test_enumerateRoles_partial( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='partial' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zrm.addRole( id, 'Role %s' % id, 'This is role, %s' % id )

        info_list = zrm.enumerateRoles( id='ba', exact_match=False )

        self.assertEqual( len( info_list ), len( ID_LIST ) - 1 ) # no 'foo'

        sorted = list( ID_LIST )
        sorted.sort()

        for i in range( len( sorted ) - 1 ):

            self.assertEqual( info_list[ i ][ 'id' ], sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'pluginid' ], 'partial' )
            self.assertEqual( info_list[ i ][ 'properties_url' ]
                            , 'partial/manage_roles?role_id=%s' % sorted[ i ])
            self.assertEqual( info_list[ i ][ 'members_url' ]
                            , 'partial/manage_roles?role_id=%s&assign=1' 
                                % sorted[ i ])
            self.assertEqual( info_list[ i ][ 'title' ]
                            , 'Role %s' % sorted[ i ] )
            self.assertEqual( info_list[ i ][ 'description' ]
                            , 'This is role, %s' % sorted[ i ] )

    def test_enumerateRoles_multiple( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='partial' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zrm.addRole( id, 'Role %s' % id, 'This is role, %s' % id )

        info_list = zrm.enumerateRoles( id=ID_LIST )

        self.assertEqual( len( info_list ), len( ID_LIST ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in ID_LIST )

        SUBSET = ID_LIST[:3]

        info_list = zrm.enumerateRoles( id=SUBSET )

        self.assertEqual( len( info_list ), len( SUBSET ) )

        for info in info_list:
            self.failUnless( info[ 'id' ] in SUBSET )

    def test_enumerateRoles_exact_nonesuch( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zgm = self._makeOne( id='exact_nonesuch' ).__of__( root )

        ID_LIST = ( 'foo', 'bar', 'baz', 'bam' )

        for id in ID_LIST:

            zgm.addRole( id, 'Role %s' % id, 'This is role, %s' % id )

        self.assertEquals( zgm.enumerateRoles( id='qux', exact_match=True )
                         , () )

    def test_assignRoleToPrincipal_nonesuch( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='assign_nonesuch' ).__of__( root )

        self.assertRaises( KeyError, zrm.assignRoleToPrincipal, 'test', 'foo' )

    def test_assignRoleToPrincipal_user( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='assign_user' ).__of__( root )
        zrm.addRole( 'test1' )
        zrm.addRole( 'test2' )
        user = DummyUser( 'foo' )

        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 0 )

        zrm.assignRoleToPrincipal( 'test1', 'foo' )

        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 1 )
        self.failUnless( 'test1' in roles )

        zrm.assignRoleToPrincipal( 'test2', 'foo' )

        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 2 )
        self.failUnless( 'test1' in roles )
        self.failUnless( 'test2' in roles )

    def test_assignRoleToPrincipal_group( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='assign_user' ).__of__( root )
        zrm.addRole( 'test1' )
        zrm.addRole( 'test2' )
        user = DummyUser( 'foo', ( 'qux', ) )

        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 0 )

        zrm.assignRoleToPrincipal( 'test1', 'qux' )

        roles = zrm.getRolesForPrincipal( user )
        self.assertEqual( len( roles ), 1 )
        self.failUnless( 'test1' in roles )

    def test_assignRoleToPrincipal_new( self ):

        root = FauxPAS()
        zrm = self._makeOne( id='assign_new' ).__of__( root )

        zrm.addRole( 'test' )
        self.assertEqual( len( zrm.listAssignedPrincipals( 'test' ) ), 0 )

        new = zrm.assignRoleToPrincipal( 'test', 'foo' )

        self.failUnless( new )

        assigned = [x[0] for x in zrm.listAssignedPrincipals( 'test' )]

        self.assertEqual( len( assigned ), 1 )
        self.assertEqual( assigned[0], 'foo' )

    def test_assignRoleToPrincipal_already( self ):

        root = FauxPAS()
        zrm = self._makeOne( id='assign_already' ).__of__( root )

        zrm.addRole( 'test' )

        zrm.assignRoleToPrincipal( 'test', 'foo' )
        new = zrm.assignRoleToPrincipal( 'test', 'foo' )

        self.failIf( new )

        assigned = [x[0] for x in zrm.listAssignedPrincipals( 'test' )]

        self.assertEqual( len( assigned ), 1 )
        self.assertEqual( assigned[0], 'foo' )

    def test_assignRoleBeforeRemovingPrincipal( self ):

        root = FauxSmartPAS()
        root.user_ids['foo'] = 'foo'

        zrm = self._makeOne( id='assign_before_remove' ).__of__( root )

        zrm.addRole( 'test' )
        self.assertEqual( len( zrm.listAssignedPrincipals( 'test' ) ), 0 )

        new = zrm.assignRoleToPrincipal( 'test', 'foo' )

        self.failUnless( new )

        assigned = [x[1] for x in zrm.listAssignedPrincipals( 'test' )]

        self.assertEqual( len( assigned ), 1 )
        self.assertEqual( assigned[0], 'foo' )

        del root.user_ids['foo']

        assigned = [x[1] for x in zrm.listAssignedPrincipals( 'test' )]

        self.assertEqual( len( assigned ), 1 )
        self.assertEqual( assigned[0], '<foo: not found>' )

    def test_removeRoleFromPrincipal_nonesuch( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='remove_nonesuch' ).__of__( root )

        self.assertRaises( KeyError, zrm.removeRoleFromPrincipal
                         , 'test', 'foo' )

    def test_removeRoleFromPrincipal_existing( self ):

        root = FauxPAS()
        zrm = self._makeOne( id='remove_existing' ).__of__( root )

        zrm.addRole( 'test' )

        zrm.assignRoleToPrincipal( 'test', 'foo' )
        zrm.assignRoleToPrincipal( 'test', 'bar' )
        zrm.assignRoleToPrincipal( 'test', 'baz' )

        assigned = [x[0] for x in zrm.listAssignedPrincipals( 'test' )]
        self.assertEqual( len( assigned ), 3 )
        self.failUnless( 'foo' in assigned )
        self.failUnless( 'bar' in assigned )
        self.failUnless( 'baz' in assigned )

        removed = zrm.removeRoleFromPrincipal( 'test', 'bar' )

        self.failUnless( removed )

        assigned = [x[0] for x in zrm.listAssignedPrincipals( 'test' )]
        self.assertEqual( len( assigned ), 2 )
        self.failUnless( 'foo' in assigned )
        self.failIf( 'bar' in assigned )
        self.failUnless( 'baz' in assigned )

    def test_removeRoleFromPrincipal_noop( self ):

        root = FauxPAS()
        zrm = self._makeOne( id='remove_noop' ).__of__( root )

        zrm.addRole( 'test' )

        zrm.assignRoleToPrincipal( 'test', 'foo' )
        zrm.assignRoleToPrincipal( 'test', 'baz' )

        assigned = [x[0] for x in zrm.listAssignedPrincipals( 'test' )]
        self.assertEqual( len( assigned ), 2 )
        self.failUnless( 'foo' in assigned )
        self.failUnless( 'baz' in assigned )

        removed = zrm.removeRoleFromPrincipal( 'test', 'bar' )

        self.failIf( removed )

    def test_updateRole_nonesuch( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='update_nonesuch' ).__of__( root )

        self.assertRaises( KeyError, zrm.updateRole
                         , 'nonesuch', 'title', 'description' )

    def test_updateRole_normal( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='update_normal' ).__of__( root )

        zrm.addRole( 'role', 'Original Title', 'Original description' )

        info = zrm.getRoleInfo( 'role' )
        self.assertEqual( info[ 'id' ], 'role' )
        self.assertEqual( info[ 'title' ], 'Original Title' )
        self.assertEqual( info[ 'description' ], 'Original description' )

        zrm.updateRole( 'role', 'Updated Title', 'Updated description' )

        info = zrm.getRoleInfo( 'role' )
        self.assertEqual( info[ 'id' ], 'role' )
        self.assertEqual( info[ 'title' ], 'Updated Title' )
        self.assertEqual( info[ 'description' ], 'Updated description' )

    def test_removeRole_then_addRole( self ):

        from Products.PluggableAuthService.tests.test_PluggableAuthService \
            import FauxRoot

        root = FauxRoot()
        zrm = self._makeOne( id='remove_then_add' ).__of__( root )
        user = DummyUser( 'foo' )

        zrm.addRole( 'test' )
        zrm.assignRoleToPrincipal( 'test', 'foo' )
        self.failUnless( 'test' in zrm.getRolesForPrincipal( user ) )

        zrm.removeRole( 'test' )
        zrm.addRole( 'test' )

        self.failIf( 'test' in zrm.getRolesForPrincipal( user ) )

if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( ZODBRoleManagerTests ),
        ))               
    
