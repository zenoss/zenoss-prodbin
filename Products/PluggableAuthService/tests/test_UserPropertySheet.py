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
from DateTime.DateTime import DateTime

from conformance import IPropertySheet_conformance

class UserPropertySheetTests( unittest.TestCase
                            , IPropertySheet_conformance
                            ):

    _SCHEMA = ( ( 's', 'string'  )
              , ( 'i', 'int'     )
              , ( 'f', 'float'   )
              , ( 'n', 'long'    )
              , ( 'd', 'date'    )
              , ( 'l', 'lines'   )
              , ( 't', 'lines'   )
              , ( 'b', 'boolean' )
              )

    _STRING_VALUE = 'string'
    _INT_VALUE = 42
    _FLOAT_VALUE = 9.8
    _LONG_VALUE = 1000000000000
    _DATE_VALUE = DateTime()
    _LIST_VALUE = [ 'a', 'b', 'c' ]
    _TUPLE_VALUE = ( 'd', 'e', 'f' )
    _BOOL_VALUE = True

    def _getTargetClass( self ):

        from Products.PluggableAuthService.UserPropertySheet \
            import UserPropertySheet

        return UserPropertySheet

    def _makeOne( self, *args, **kw ):

        return self._getTargetClass()( *args, **kw )

    def test_ctor_id_noschema_novalues( self ):

        ups = self._makeOne( 'empty' )

        self.assertEqual( ups.getId(), 'empty' )

        self.failIf( ups.hasProperty( 'empty' ) )
        self.failIf( ups.hasProperty( 'foo' ) )
        self.failIf( ups.hasProperty( 'bar' ) )

        self.assertEqual( ups.getProperty( 'foo' ), None )
        self.assertEqual( ups.getPropertyType( 'foo' ), None )

        self.assertEqual( len( ups.propertyMap() ), 0 )
        self.assertEqual( len( ups.propertyIds() ), 0 )
        self.assertEqual( len( ups.propertyValues() ), 0 )
        self.assertEqual( len( ups.propertyItems() ), 0 )
        self.assertEqual( len( ups.propertyIds() ), 0 )

    def _checkStockSchema( self, ups ):

        self.failIf( ups.hasProperty( 'x' ) )
        self.failUnless( ups.hasProperty( 's' ) )
        self.failUnless( ups.hasProperty( 'i' ) )
        self.failUnless( ups.hasProperty( 'f' ) )
        self.failUnless( ups.hasProperty( 'n' ) )
        self.failUnless( ups.hasProperty( 'd' ) )
        self.failUnless( ups.hasProperty( 'l' ) )
        self.failUnless( ups.hasProperty( 't' ) )
        self.failUnless( ups.hasProperty( 'b' ) )

        self.assertEqual( ups.getPropertyType( 's' ), 'string' )
        self.assertEqual( ups.propertyInfo( 's' )[ 'type' ], 'string' )
        self.assertEqual( ups.getProperty( 's' ), self._STRING_VALUE )

        self.assertEqual( ups.getPropertyType( 'i' ), 'int' )
        self.assertEqual( ups.propertyInfo( 'i' )[ 'type' ], 'int' )
        self.assertEqual( ups.getProperty( 'i' ), self._INT_VALUE )

        self.assertEqual( ups.getPropertyType( 'f' ), 'float' )
        self.assertEqual( ups.propertyInfo( 'f' )[ 'type' ], 'float' )
        self.assertEqual( ups.getProperty( 'f' ), self._FLOAT_VALUE )

        self.assertEqual( ups.getPropertyType( 'n' ), 'long' )
        self.assertEqual( ups.propertyInfo( 'n' )[ 'type' ], 'long' )
        self.assertEqual( ups.getProperty( 'n' ), self._LONG_VALUE )

        self.assertEqual( ups.getPropertyType( 'd' ), 'date' )
        self.assertEqual( ups.propertyInfo( 'd' )[ 'type' ], 'date' )
        self.assertEqual( ups.getProperty( 'd' ), self._DATE_VALUE )

        self.assertEqual( ups.getPropertyType( 'b' ), 'boolean' )
        self.assertEqual( ups.propertyInfo( 'b' )[ 'type' ], 'boolean' )
        self.assertEqual( ups.getProperty( 'b' ), self._BOOL_VALUE )

        self.assertEqual( ups.getPropertyType( 'l' ), 'lines' )
        self.assertEqual( ups.propertyInfo( 'l' )[ 'type' ], 'lines' )

        got = ups.getProperty( 'l' )
        self.assertEqual( type( got ), type( () ) )
        self.assertEqual( len( got ), len( self._LIST_VALUE ) )

        for i in range( len( self._LIST_VALUE ) ):
            self.assertEqual( got[i], self._LIST_VALUE[i] )

        self.assertEqual( ups.getPropertyType( 't' ), 'lines' )
        self.assertEqual( ups.propertyInfo( 't' )[ 'type' ], 'lines' )

        got = ups.getProperty( 't' )
        self.assertEqual( type( got ), type( () ) )
        self.assertEqual( len( got ), len( self._TUPLE_VALUE ) )

        for i in range( len( self._TUPLE_VALUE ) ):
            self.assertEqual( got[i], self._TUPLE_VALUE[i] )

        pmap = ups.propertyMap()
        self.assertEqual( len( pmap ), len( self._SCHEMA ) )

        for i in range( len( pmap ) ):
            info = pmap[i]
            spec = [ x for x in self._SCHEMA if x[0] == info['id' ] ][0]
            self.assertEqual( info[ 'id' ], spec[0] )
            self.assertEqual( info[ 'type' ], spec[1] )
            self.assertEqual( info[ 'mode' ], '' )  # readonly, no delete


    def test_ctor__guessSchema( self ):

        ups = self._makeOne( 'guessed'
                           , s=self._STRING_VALUE
                           , i=self._INT_VALUE
                           , f=self._FLOAT_VALUE
                           , n=self._LONG_VALUE
                           , d=self._DATE_VALUE
                           , l=self._LIST_VALUE
                           , t=self._TUPLE_VALUE
                           , b=self._BOOL_VALUE
                           )

        self._checkStockSchema( ups )


    def test_ctor_w_schema(self):

        ups = self._makeOne( 'w_schema'
                           , self._SCHEMA
                           , s=self._STRING_VALUE
                           , i=self._INT_VALUE
                           , f=self._FLOAT_VALUE
                           , n=self._LONG_VALUE
                           , d=self._DATE_VALUE
                           , l=self._LIST_VALUE
                           , t=self._TUPLE_VALUE
                           , b=self._BOOL_VALUE
                           )

        self._checkStockSchema( ups )

if __name__ == "__main__":
    unittest.main()

def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( UserPropertySheetTests ),
        ))
