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

from OFS.SimpleItem import SimpleItem
from Products.PluggableAuthService.tests.conformance \
    import IGroupsPlugin_conformance

from Products.PluggableAuthService.tests.test_PluggableAuthService \
    import FauxContainer

class FauxPAS( FauxContainer ):

    def __init__( self ):
        self._id = 'acl_users'
        
    def _getGroupsForPrincipal( self, principal, request=None, plugins=None
                              , ignore_plugins=None ):
        all_groups = []

        if ignore_plugins is None:
            ignore_plugins = ()

        for plugin in self.objectValues():
            if plugin.getId() in ignore_plugins:
                continue
            groups = plugin.getGroupsForPrincipal( principal, request )
            groups = [ '%s:%s' % ( plugin.getId(), x ) for x in groups ]
            all_groups.extend( groups )

        return all_groups

class DummyPrincipal:
    
    def __init__( self, id, groups=() ):
        self._id = id
        self._groups = groups
        
    def getId( self ):
        return self._id
        
    def getGroups( self ):
        return self._groups

class DummyGroupsManager( SimpleItem ):

    def __init__( self, id ):
        self._id = id
        self._groups = {}
        self._prin_to_group = {}

    def getId( self ):
        return self._id
    
    def addGroup( self, group_id ):
        self._groups[group_id] = 1
        
    def addPrincipalToGroup( self, prin, group_id ):
        prin_id = prin.getId()
        already_in = self._prin_to_group.get( prin_id, () )
        if group_id not in already_in:
            self._prin_to_group[prin_id] = already_in + ( group_id, )

    def getGroupsForPrincipal( self, prin, request=None ):
        prin_id = prin.getId()
        return self._prin_to_group.get( prin_id, () )

class RecursiveGroupsPluginTests( unittest.TestCase
                                , IGroupsPlugin_conformance
                                ):

    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.RecursiveGroupsPlugin \
            import RecursiveGroupsPlugin

        return RecursiveGroupsPlugin

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id=id, *args, **kw )

    def test_simple_flattening( self ):
        
        pas = FauxPAS()
        dgm = DummyGroupsManager( 'dummy' )
        rgp = self._makeOne( 'rgp' )

        pas._setObject( 'dgm', dgm )
        pas._setObject( 'rgp', rgp )

        dgm = pas._getOb( 'dgm' )
        dgm.addGroup( 'group1' )
        dgm.addGroup( 'group2' )
        
        rgp = pas._getOb( 'rgp' )

        user = DummyPrincipal( 'user1', ( 'dummy:group1', ) )
                
        dgm.addPrincipalToGroup( user, 'group1' )
        dgm.addPrincipalToGroup( DummyPrincipal( 'dummy:group1' ), 'group2' )
        
        self.assertEqual( rgp.getGroupsForPrincipal( user )
                        , ( 'dummy:group1', 'dummy:group2' ) 
                        )

    def test_complex_flattening( self ):
        
        pas = FauxPAS()
        dgm = DummyGroupsManager( 'dummy' )
        odgm = DummyGroupsManager( 'other_dummy' )
        rgp = self._makeOne( 'rgp' )

        pas._setObject( 'dgm', dgm )
        pas._setObject( 'odgm', odgm )
        pas._setObject( 'rgp', rgp )

        dgm = pas._getOb( 'dgm' )
        dgm.addGroup( 'group1' )
        dgm.addGroup( 'group2' )

        odgm = pas._getOb( 'odgm' )
        odgm.addGroup( 'group3' )
        odgm.addGroup( 'group4' )

        rgp = pas._getOb( 'rgp' )
        
        user = DummyPrincipal( 'user1', ( 'dummy:group1'
                                        , 'other_dummy:group3' ) )
                
        dgm.addPrincipalToGroup( user, 'group1' )
        dgm.addPrincipalToGroup( DummyPrincipal( 'dummy:group1' ), 'group2' )

        odgm.addPrincipalToGroup( user, 'group3' )
        odgm.addPrincipalToGroup( DummyPrincipal( 'dummy:group2' ), 'group4' )
        
        groups = rgp.getGroupsForPrincipal( user )
        self.assertEqual( len( groups ), 4 )
        self.failUnless( 'dummy:group1' in groups )
        self.failUnless( 'dummy:group2' in groups )
        self.failUnless( 'other_dummy:group3' in groups )
        self.failUnless( 'other_dummy:group4' in groups )

    def test_cross_nested_flattening( self ):
        
        pas = FauxPAS()
        dgm = DummyGroupsManager( 'dummy' )
        odgm = DummyGroupsManager( 'other_dummy' )
        rgp = self._makeOne( 'rgp' )

        pas._setObject( 'dgm', dgm )
        pas._setObject( 'odgm', odgm )
        pas._setObject( 'rgp', rgp )

        dgm = pas._getOb( 'dgm' )
        dgm.addGroup( 'group1' )

        odgm = pas._getOb( 'odgm' )
        odgm.addGroup( 'group2' )

        rgp = pas._getOb( 'rgp' )
        
        user = DummyPrincipal( 'user1', ( 'dummy:group1'
                                        , 'other_dummy:group2' ) )
                
        dgm.addPrincipalToGroup( user, 'group1' )
        dgm.addPrincipalToGroup( DummyPrincipal( 'other_dummy:group1' )
                               , 'group1' )

        odgm.addPrincipalToGroup( user, 'group2' )
        odgm.addPrincipalToGroup( DummyPrincipal( 'dummy:group1' ), 'group2' )
        
        groups = rgp.getGroupsForPrincipal( user )
        self.assertEqual( len( groups ), 2 )
        self.failUnless( 'dummy:group1' in groups )
        self.failUnless( 'other_dummy:group2' in groups )

if __name__ == "__main__":
    unittest.main()


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( RecursiveGroupsPluginTests ),
        ))
