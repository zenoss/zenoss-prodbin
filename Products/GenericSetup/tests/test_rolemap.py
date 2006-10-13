##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" GenericSetup rolemap export / import unit tests

$Id: test_rolemap.py 68488 2006-06-04 17:22:57Z yuppie $
"""

import unittest
import Testing

from OFS.Folder import Folder

from common import BaseRegistryTests
from common import DummyExportContext
from common import DummyImportContext


class RolemapConfiguratorTests( BaseRegistryTests ):

    def _getTargetClass( self ):

        from Products.GenericSetup.rolemap import RolemapConfigurator
        return RolemapConfigurator

    def test_listRoles_normal( self ):

        EXPECTED = [ 'Anonymous', 'Authenticated', 'Manager', 'Owner' ]
        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        roles = list( configurator.listRoles() )
        self.assertEqual( len( roles ), len( EXPECTED ) )

        roles.sort()

        for found, expected in zip( roles, EXPECTED ):
            self.assertEqual( found, expected )

    def test_listRoles_added( self ):

        EXPECTED = [ 'Anonymous', 'Authenticated', 'Manager', 'Owner', 'ZZZ' ]
        self.root.site = Folder( id='site' )
        site = self.root.site
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        existing_roles.append( 'ZZZ' )
        site.__ac_roles__ = existing_roles

        configurator = self._makeOne( site )

        roles = list( configurator.listRoles() )
        self.assertEqual( len( roles ), len( EXPECTED ) )

        roles.sort()

        for found, expected in zip( roles, EXPECTED ):
            self.assertEqual( found, expected )

    def test_listPermissions_nooverrides( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        self.assertEqual( len( configurator.listPermissions() ), 0 )

    def test_listPermissions_nooverrides( self ):

        site = Folder( id='site' ).__of__( self.root )
        configurator = self._makeOne( site )

        self.assertEqual( len( configurator.listPermissions() ), 0 )

    def test_listPermissions_acquire( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        site = Folder( id='site' ).__of__( self.root )
        site.manage_permission( ACI, ROLES, acquire=1 )
        configurator = self._makeOne( site )

        self.assertEqual( len( configurator.listPermissions() ), 1 )
        info = configurator.listPermissions()[ 0 ]
        self.assertEqual( info[ 'name' ], ACI )
        self.assertEqual( info[ 'roles' ], ROLES )
        self.failUnless( info[ 'acquire' ] )

    def test_listPermissions_no_acquire( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        site = Folder( id='site' ).__of__( self.root )
        site.manage_permission( ACI, ROLES )
        configurator = self._makeOne( site )

        self.assertEqual( len( configurator.listPermissions() ), 1 )
        info = configurator.listPermissions()[ 0 ]
        self.assertEqual( info[ 'name' ], ACI )
        self.assertEqual( info[ 'roles' ], ROLES )
        self.failIf( info[ 'acquire' ] )

    def test_generateXML_empty( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site ).__of__( site )

        self._compareDOM( configurator.generateXML(), _EMPTY_EXPORT )

    def test_generateXML_added_role( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        existing_roles.append( 'ZZZ' )
        site.__ac_roles__ = existing_roles
        configurator = self._makeOne( site ).__of__( site )

        self._compareDOM( configurator.generateXML(), _ADDED_ROLE_EXPORT )

    def test_generateEXML_acquired_perm( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        site = Folder( id='site' ).__of__( self.root )
        site.manage_permission( ACI, ROLES, acquire=1 )
        configurator = self._makeOne( site ).__of__( site )

        self._compareDOM( configurator.generateXML(), _ACQUIRED_EXPORT )

    def test_generateEXML_unacquired_perm( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner', 'ZZZ' ]

        site = Folder( id='site' ).__of__( self.root )
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        existing_roles.append( 'ZZZ' )
        site.__ac_roles__ = existing_roles
        site.manage_permission( ACI, ROLES )
        configurator = self._makeOne( site ).__of__( site )

        self._compareDOM( configurator.generateXML(), _COMBINED_EXPORT )

    def test_generateEXML_unacquired_perm_added_role( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        site = Folder( id='site' ).__of__( self.root )
        site.manage_permission( ACI, ROLES )
        configurator = self._makeOne( site ).__of__( site )

        self._compareDOM( configurator.generateXML(), _UNACQUIRED_EXPORT )

    def test_parseXML_empty( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        configurator = self._makeOne( site )

        rolemap_info = configurator.parseXML( _EMPTY_EXPORT )

        self.assertEqual( len( rolemap_info[ 'roles' ] ), 4 )
        self.assertEqual( len( rolemap_info[ 'permissions' ] ), 0 )

    def test_parseXML_added_role( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        rolemap_info = configurator.parseXML( _ADDED_ROLE_EXPORT )
        roles = rolemap_info[ 'roles' ]

        self.assertEqual( len( roles ), 5 )
        self.failUnless( 'Anonymous' in roles )
        self.failUnless( 'Authenticated' in roles )
        self.failUnless( 'Manager' in roles )
        self.failUnless( 'Owner' in roles )
        self.failUnless( 'ZZZ' in roles )

    def test_parseXML_acquired_permission( self ):

        ACI = 'Access contents information'

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        rolemap_info = configurator.parseXML( _ACQUIRED_EXPORT )

        self.assertEqual( len( rolemap_info[ 'permissions' ] ), 1 )
        permission = rolemap_info[ 'permissions' ][ 0 ]

        self.assertEqual( permission[ 'name' ], ACI )
        self.failUnless( permission[ 'acquire' ] )

        p_roles = permission[ 'roles' ]
        self.assertEqual( len( p_roles ), 2 )
        self.failUnless( 'Manager' in p_roles )
        self.failUnless( 'Owner' in p_roles )

    def test_parseXML_unacquired_permission( self ):

        ACI = 'Access contents information'

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        rolemap_info = configurator.parseXML( _UNACQUIRED_EXPORT )

        self.assertEqual( len( rolemap_info[ 'permissions' ] ), 1 )
        permission = rolemap_info[ 'permissions' ][ 0 ]

        self.assertEqual( permission[ 'name' ], ACI )
        self.failIf( permission[ 'acquire' ] )

        p_roles = permission[ 'roles' ]
        self.assertEqual( len( p_roles ), 2 )
        self.failUnless( 'Manager' in p_roles )
        self.failUnless( 'Owner' in p_roles )

    def test_parseXML_unacquired_permission_added_role( self ):

        ACI = 'Access contents information'

        self.root.site = Folder( id='site' )
        site = self.root.site
        configurator = self._makeOne( site )

        rolemap_info = configurator.parseXML( _COMBINED_EXPORT )
        roles = rolemap_info[ 'roles' ]

        self.assertEqual( len( roles ), 5 )
        self.failUnless( 'Anonymous' in roles )
        self.failUnless( 'Authenticated' in roles )
        self.failUnless( 'Manager' in roles )
        self.failUnless( 'Owner' in roles )
        self.failUnless( 'ZZZ' in roles )

        self.assertEqual( len( rolemap_info[ 'permissions' ] ), 1 )
        permission = rolemap_info[ 'permissions' ][ 0 ]

        self.assertEqual( permission[ 'name' ], ACI )
        self.failIf( permission[ 'acquire' ] )

        p_roles = permission[ 'roles' ]
        self.assertEqual( len( p_roles ), 3 )
        self.failUnless( 'Manager' in p_roles )
        self.failUnless( 'Owner' in p_roles )
        self.failUnless( 'ZZZ' in p_roles )



_EMPTY_EXPORT = """\
<?xml version="1.0"?>
<rolemap>
  <roles>
    <role name="Anonymous"/>
    <role name="Authenticated"/>
    <role name="Manager"/>
    <role name="Owner"/>
  </roles>
  <permissions>
  </permissions>
</rolemap>
"""

_ADDED_ROLE_EXPORT = """\
<?xml version="1.0"?>
<rolemap>
  <roles>
    <role name="Anonymous"/>
    <role name="Authenticated"/>
    <role name="Manager"/>
    <role name="Owner"/>
    <role name="ZZZ"/>
  </roles>
  <permissions>
  </permissions>
</rolemap>
"""

_ACQUIRED_EXPORT = """\
<?xml version="1.0"?>
<rolemap>
  <roles>
    <role name="Anonymous"/>
    <role name="Authenticated"/>
    <role name="Manager"/>
    <role name="Owner"/>
  </roles>
  <permissions>
    <permission name="Access contents information"
                acquire="True">
      <role name="Manager"/>
      <role name="Owner"/>
    </permission>
  </permissions>
</rolemap>
"""

_UNACQUIRED_EXPORT = """\
<?xml version="1.0"?>
<rolemap>
  <roles>
    <role name="Anonymous"/>
    <role name="Authenticated"/>
    <role name="Manager"/>
    <role name="Owner"/>
  </roles>
  <permissions>
    <permission name="Access contents information"
                acquire="False">
      <role name="Manager"/>
      <role name="Owner"/>
    </permission>
  </permissions>
</rolemap>
"""

_COMBINED_EXPORT = """\
<?xml version="1.0"?>
<rolemap>
  <roles>
    <role name="Anonymous"/>
    <role name="Authenticated"/>
    <role name="Manager"/>
    <role name="Owner"/>
    <role name="ZZZ"/>
  </roles>
  <permissions>
    <permission name="Access contents information"
                acquire="False">
      <role name="Manager"/>
      <role name="Owner"/>
      <role name="ZZZ"/>
    </permission>
  </permissions>
</rolemap>
"""

class Test_exportRolemap( BaseRegistryTests ):

    def test_unchanged( self ):

        self.root.site = Folder( 'site' )
        site = self.root.site

        context = DummyExportContext( site )

        from Products.GenericSetup.rolemap import exportRolemap
        exportRolemap( context )

        self.assertEqual( len( context._wrote ), 1 )
        filename, text, content_type = context._wrote[ 0 ]
        self.assertEqual( filename, 'rolemap.xml' )
        self._compareDOM( text, _EMPTY_EXPORT )
        self.assertEqual( content_type, 'text/xml' )

    def test_added_role( self ):

        self.root.site = Folder( 'site' )
        site = self.root.site
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        existing_roles.append( 'ZZZ' )
        site.__ac_roles__ = existing_roles

        context = DummyExportContext( site )

        from Products.GenericSetup.rolemap import exportRolemap
        exportRolemap( context )

        self.assertEqual( len( context._wrote ), 1 )
        filename, text, content_type = context._wrote[ 0 ]
        self.assertEqual( filename, 'rolemap.xml' )
        self._compareDOM( text, _ADDED_ROLE_EXPORT )
        self.assertEqual( content_type, 'text/xml' )


    def test_acquired_perm( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        self.root.site = Folder( 'site' )
        site = self.root.site
        site.manage_permission( ACI, ROLES, acquire=1 )

        context = DummyExportContext( site )

        from Products.GenericSetup.rolemap import exportRolemap
        exportRolemap( context )

        self.assertEqual( len( context._wrote ), 1 )
        filename, text, content_type = context._wrote[ 0 ]
        self.assertEqual( filename, 'rolemap.xml' )
        self._compareDOM( text, _ACQUIRED_EXPORT )
        self.assertEqual( content_type, 'text/xml' )

    def test_unacquired_perm( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner', 'ZZZ' ]

        self.root.site = Folder( 'site' )
        site = self.root.site
        existing_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        existing_roles.append( 'ZZZ' )
        site.__ac_roles__ = existing_roles
        site.manage_permission( ACI, ROLES )

        context = DummyExportContext( site )

        from Products.GenericSetup.rolemap import exportRolemap
        exportRolemap( context )

        self.assertEqual( len( context._wrote ), 1 )
        filename, text, content_type = context._wrote[ 0 ]
        self.assertEqual( filename, 'rolemap.xml' )
        self._compareDOM( text, _COMBINED_EXPORT )
        self.assertEqual( content_type, 'text/xml' )

    def test_unacquired_perm_added_role( self ):

        ACI = 'Access contents information'
        ROLES = [ 'Manager', 'Owner' ]

        self.root.site = Folder( 'site' )
        site = self.root.site
        site.manage_permission( ACI, ROLES )

        context = DummyExportContext( site )

        from Products.GenericSetup.rolemap import exportRolemap
        exportRolemap( context )

        self.assertEqual( len( context._wrote ), 1 )
        filename, text, content_type = context._wrote[ 0 ]
        self.assertEqual( filename, 'rolemap.xml' )
        self._compareDOM( text, _UNACQUIRED_EXPORT )
        self.assertEqual( content_type, 'text/xml' )

class Test_importRolemap( BaseRegistryTests ):

    def test_empty_default_purge( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        original_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        modified_roles = original_roles[:]
        modified_roles.append( 'ZZZ' )
        site.__ac_roles__ = modified_roles

        context = DummyImportContext( site )
        context._files[ 'rolemap.xml' ] = _EMPTY_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_roles = list( getattr( site, '__ac_roles__', [] ) )[:]

        original_roles.sort()
        new_roles.sort()

        self.assertEqual( original_roles, new_roles )

    def test_empty_explicit_purge( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        original_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        modified_roles = original_roles[:]
        modified_roles.append( 'ZZZ' )
        site.__ac_roles__ = modified_roles

        context = DummyImportContext( site, True )
        context._files[ 'rolemap.xml' ] = _EMPTY_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_roles = list( getattr( site, '__ac_roles__', [] ) )[:]

        original_roles.sort()
        new_roles.sort()

        self.assertEqual( original_roles, new_roles )

    def test_empty_skip_purge( self ):

        self.root.site = Folder( id='site' )
        site = self.root.site
        original_roles = list( getattr( site, '__ac_roles__', [] ) )[:]
        modified_roles = original_roles[:]
        modified_roles.append( 'ZZZ' )
        site.__ac_roles__ = modified_roles

        context = DummyImportContext( site, False )
        context._files[ 'rolemap.xml' ] = _EMPTY_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_roles = list( getattr( site, '__ac_roles__', [] ) )[:]

        modified_roles.sort()
        new_roles.sort()

        self.assertEqual( modified_roles, new_roles )

    def test_acquired_permission_explicit_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( ACI, () )
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        context = DummyImportContext( site, True )
        context._files[ 'rolemap.xml' ] = _ACQUIRED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner' ] )

        # ACI is overwritten by XML, but VIEW was purged
        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failUnless( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_acquired_permission_no_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( ACI, () )
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )

        context = DummyImportContext( site, False )
        context._files[ 'rolemap.xml' ] = _ACQUIRED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner' ] )

        # ACI is overwritten by XML, but VIEW is not
        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_unacquired_permission_explicit_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [ 'Manager' ] )

        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        context = DummyImportContext( site, True )
        context._files[ 'rolemap.xml' ] = _UNACQUIRED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner' ] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failUnless( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_unacquired_permission_skip_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [ 'Manager' ] )

        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        context = DummyImportContext( site, False )
        context._files[ 'rolemap.xml' ] = _UNACQUIRED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner' ] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_unacquired_permission_added_role_explicit_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [ 'Manager' ] )

        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        self.failIf( site._has_user_defined_role( 'ZZZ' ) )

        context = DummyImportContext( site, True )
        context._files[ 'rolemap.xml' ] = _COMBINED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        self.failUnless( site._has_user_defined_role( 'ZZZ' ) )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner', 'ZZZ' ] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failUnless( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_unacquired_permission_added_role_skip_purge( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [ 'Manager' ] )

        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        self.failIf( site._has_user_defined_role( 'ZZZ' ) )

        context = DummyImportContext( site, False )
        context._files[ 'rolemap.xml' ] = _COMBINED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        self.failUnless( site._has_user_defined_role( 'ZZZ' ) )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner', 'ZZZ' ] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

    def test_unacquired_permission_added_role_skip_purge_encode_ascii( self ):

        ACI = 'Access contents information'
        VIEW = 'View'

        self.root.site = Folder( id='site' )
        site = self.root.site
        site.manage_permission( VIEW, () )

        existing_allowed = [ x[ 'name' ]
                                for x in site.rolesOfPermission( ACI )
                                if x[ 'selected' ] ]

        self.assertEqual( existing_allowed, [ 'Manager' ] )

        self.failUnless( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )

        self.failIf( site._has_user_defined_role( 'ZZZ' ) )

        context = DummyImportContext( site, False, encoding='ascii' )
        context._files[ 'rolemap.xml' ] = _COMBINED_EXPORT

        from Products.GenericSetup.rolemap import importRolemap
        importRolemap( context )

        self.failUnless( site._has_user_defined_role( 'ZZZ' ) )

        new_allowed = [ x[ 'name' ]
                           for x in site.rolesOfPermission( ACI )
                           if x[ 'selected' ] ]

        self.assertEqual( new_allowed, [ 'Manager', 'Owner', 'ZZZ' ] )

        self.failIf( site.acquiredRolesAreUsedBy( ACI ) )
        self.failIf( site.acquiredRolesAreUsedBy( VIEW ) )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( RolemapConfiguratorTests ),
        unittest.makeSuite( Test_exportRolemap ),
        unittest.makeSuite( Test_importRolemap ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
