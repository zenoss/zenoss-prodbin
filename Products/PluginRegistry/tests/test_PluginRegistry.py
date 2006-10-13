##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import unittest
from OFS.Folder import Folder

try:
    from zope.interface import Interface
except ImportError:  # Zope < 2.8.0
    from Interface import Interface

from Acquisition import Implicit

from Products.PluginRegistry.utils import directlyProvides

class INonesuch(Interface):
    pass

class IFoo(Interface):
    def foo():
        """ Foo. """

class IBar(Interface):
    def bar():
        """ Bar. """

class DummyFolder(Folder):
    pass

class DummyPlugin(Implicit):
    pass

_PLUGIN_INFO = ( ( IFoo, 'IFoo', 'foo', 'Foo test' )
               , ( IBar, 'IBar', 'bar', 'Bar test' )
               )

class PluginRegistryTests( unittest.TestCase ):

    def _getTargetClass( self ):

        from Products.PluginRegistry.PluginRegistry import PluginRegistry

        return PluginRegistry

    def _makeOne( self, plugin_info=_PLUGIN_INFO, *args, **kw ):

        return self._getTargetClass()( plugin_info, *args, **kw )

    def test_conformance_to_IPluginRegistry( self ):

        from Products.PluginRegistry.interfaces import IPluginRegistry
        from Products.PluginRegistry.interfaces import _HAS_Z3_INTERFACES

        if _HAS_Z3_INTERFACES:
            from zope.interface.verify import verifyClass
        else:
            from Interface.Verify import verifyClass

        verifyClass( IPluginRegistry, self._getTargetClass() )


    def test_empty( self ):

        preg = self._makeOne()

        self.assertRaises( KeyError, preg.listPlugins, INonesuch )
        self.assertEqual( len( preg.listPlugins( IFoo ) ), 0 )
        self.assertEqual( len( preg.listPluginIds( IFoo ) ), 0 )

    def test_listPluginTypeInfo( self ):

        pref = self._makeOne()

        pti = pref.listPluginTypeInfo()
        self.assertEqual( pti[0]['interface'], IFoo )
        self.assertEqual( pti[1]['title'], 'bar' )

    def test_activatePluginNoChild( self ):

        parent = DummyFolder()

        preg = self._makeOne().__of__(parent)

        self.assertRaises( AttributeError, preg.activatePlugin, IFoo,
                           'foo_plugin' )

    def test_activatePluginInterfaceNonconformance( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        parent._setObject( 'foo_plugin', foo_plugin )

        preg = self._makeOne().__of__(parent)

        self.assertRaises( ValueError, preg.activatePlugin, IFoo,
                           'foo_plugin' )

    def test_activatePlugin( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin,  ( IFoo, ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        preg = self._makeOne().__of__(parent)

        preg.activatePlugin( IFoo, 'foo_plugin')

        idlist = preg.listPluginIds( IFoo )
        self.assertEqual( len( idlist ), 1 )
        self.assertEqual( idlist[0], 'foo_plugin' )

        # XXX:  Note that we aren't testing 'listPlugins' here, as it
        #       requires that we have TALES wired up.
        #
        #plugins = preg.listPlugins( 'foo' )
        #self.assertEqual( len( plugins ), 1 )
        #plugin = plugins[0]
        #self.assertEqual( plugin[0], 'test' )
        #self.assertEqual( plugin[1], preg.test_foo )

    def test_deactivatePlugin( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin, ( IFoo, ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        bar_plugin = DummyPlugin()
        directlyProvides( bar_plugin, ( IFoo, ) )
        parent._setObject( 'bar_plugin', bar_plugin )

        baz_plugin = DummyPlugin()
        directlyProvides( baz_plugin, ( IFoo, ) )
        parent._setObject( 'baz_plugin', baz_plugin )

        preg = self._makeOne().__of__(parent)

        preg.activatePlugin( IFoo, 'foo_plugin' )
        preg.activatePlugin( IFoo, 'bar_plugin' )
        preg.activatePlugin( IFoo, 'baz_plugin' )

        preg.deactivatePlugin( IFoo, 'bar_plugin' )

        idlist = preg.listPluginIds( IFoo )
        self.assertEqual( len( idlist ), 2 )
        self.assertEqual( idlist[0], 'foo_plugin' )
        self.assertEqual( idlist[1], 'baz_plugin' )

    def test_movePluginsUp( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin, ( IFoo, ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        bar_plugin = DummyPlugin()
        directlyProvides( bar_plugin, ( IFoo, ) )
        parent._setObject( 'bar_plugin', bar_plugin )

        baz_plugin = DummyPlugin()
        directlyProvides( baz_plugin, ( IFoo, ) )
        parent._setObject( 'baz_plugin', baz_plugin )

        preg = self._makeOne().__of__(parent)

        preg.activatePlugin( IFoo, 'foo_plugin' )
        preg.activatePlugin( IFoo, 'bar_plugin' )
        preg.activatePlugin( IFoo, 'baz_plugin' )

        self.assertRaises( ValueError, preg.movePluginsUp
                         , IFoo, ( 'quux_plugin', ) )

        preg.movePluginsUp( IFoo, ( 'bar_plugin', 'baz_plugin' ) )

        idlist = preg.listPluginIds( IFoo )
        self.assertEqual( len( idlist ), 3 )

        self.assertEqual( idlist[0], 'bar_plugin' )
        self.assertEqual( idlist[1], 'baz_plugin' )
        self.assertEqual( idlist[2], 'foo_plugin' )

    def test_movePluginsDown( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin, ( IFoo, ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        bar_plugin = DummyPlugin()
        directlyProvides( bar_plugin, ( IFoo, ) )
        parent._setObject( 'bar_plugin', bar_plugin )

        baz_plugin = DummyPlugin()
        directlyProvides( baz_plugin, ( IFoo, ) )
        parent._setObject( 'baz_plugin', baz_plugin )

        preg = self._makeOne().__of__(parent)

        preg.activatePlugin( IFoo, 'foo_plugin' )
        preg.activatePlugin( IFoo, 'bar_plugin' )
        preg.activatePlugin( IFoo, 'baz_plugin' )

        self.assertRaises( ValueError, preg.movePluginsDown
                         , IFoo, ( 'quux_plugin', ) )

        preg.movePluginsDown( IFoo, ( 'foo_plugin', 'bar_plugin' ) )

        idlist = preg.listPluginIds( IFoo )
        self.assertEqual( len( idlist ), 3 )

        self.assertEqual( idlist[0], 'baz_plugin' )
        self.assertEqual( idlist[1], 'foo_plugin' )
        self.assertEqual( idlist[2], 'bar_plugin' )

    def test_getAllPlugins( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin, ( IFoo, ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        bar_plugin = DummyPlugin()
        directlyProvides( bar_plugin, ( IFoo, ) )
        parent._setObject( 'bar_plugin', bar_plugin )

        baz_plugin = DummyPlugin()
        directlyProvides( baz_plugin, ( IFoo, ) )
        parent._setObject( 'baz_plugin', baz_plugin )

        preg = self._makeOne().__of__( parent )

        first = preg.getAllPlugins( 'IFoo' )

        self.assertEqual( len( first[ 'active' ] ), 0 )

        self.assertEqual( len( first[ 'available' ] ), 3 )
        self.failUnless( 'foo_plugin' in first[ 'available' ] )
        self.failUnless( 'bar_plugin' in first[ 'available' ] )
        self.failUnless( 'baz_plugin' in first[ 'available' ] )

        preg.activatePlugin( IFoo, 'foo_plugin' )

        second = preg.getAllPlugins( 'IFoo' )

        self.assertEqual( len( second[ 'active' ] ), 1 )
        self.failUnless( 'foo_plugin' in second[ 'active' ] )

        self.assertEqual( len( second[ 'available' ] ), 2 )
        self.failIf( 'foo_plugin' in second[ 'available' ] )
        self.failUnless( 'bar_plugin' in second[ 'available' ] )
        self.failUnless( 'baz_plugin' in second[ 'available' ] )

        preg.activatePlugin( IFoo, 'bar_plugin' )
        preg.activatePlugin( IFoo, 'baz_plugin' )

        third = preg.getAllPlugins( 'IFoo' )

        self.assertEqual( len( third[ 'active' ] ), 3 )
        self.failUnless( 'foo_plugin' in third[ 'active' ] )
        self.failUnless( 'bar_plugin' in third[ 'active' ] )
        self.failUnless( 'baz_plugin' in third[ 'active' ] )

        self.assertEqual( len( third[ 'available' ] ), 0 )

    def test_removePluginById( self ):

        parent = DummyFolder()
        foo_plugin = DummyPlugin()
        directlyProvides( foo_plugin, ( IFoo, IBar ) )
        parent._setObject( 'foo_plugin', foo_plugin )

        bar_plugin = DummyPlugin()
        directlyProvides( bar_plugin, ( IFoo, ) )
        parent._setObject( 'bar_plugin', bar_plugin )

        baz_plugin = DummyPlugin()
        directlyProvides( baz_plugin, ( IBar, ) )
        parent._setObject( 'baz_plugin', baz_plugin )

        preg = self._makeOne().__of__(parent)

        preg.activatePlugin( IFoo, 'foo_plugin' )
        preg.activatePlugin( IBar, 'foo_plugin' )
        preg.activatePlugin( IFoo, 'bar_plugin' )
        preg.activatePlugin( IBar, 'baz_plugin' )

        preg.removePluginById( 'foo_plugin' )

        idlist = preg.listPluginIds( IFoo )
        self.assertEqual( len( idlist ), 1 )
        self.assertEqual( idlist[0], 'bar_plugin' )

        idlist = preg.listPluginIds( IBar )
        self.assertEqual( len( idlist ), 1 )
        self.assertEqual( idlist[0], 'baz_plugin' )

if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( PluginRegistryTests ),
        ))
