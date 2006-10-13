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
""" Unit tests for import / export contexts.

$Id: test_context.py 41502 2006-01-30 17:48:12Z efge $
"""

import unittest
import Testing

import logging
import os
import time
from StringIO import StringIO
from tarfile import TarFile
from tarfile import TarInfo

from DateTime.DateTime import DateTime
from OFS.Folder import Folder
from OFS.Image import File

from common import FilesystemTestBase
from common import SecurityRequestTest
from common import TarballTester
from common import _makeTestFile
from conformance import ConformsToISetupContext
from conformance import ConformsToIImportContext
from conformance import ConformsToIExportContext


class DummySite( Folder ):

    pass

class DummyTool( Folder ):

    pass


class DirectoryImportContextTests( FilesystemTestBase
                                 , ConformsToISetupContext
                                 , ConformsToIImportContext
                                 ):

    _PROFILE_PATH = '/tmp/ICTTexts'

    def _getTargetClass( self ):

        from Products.GenericSetup.context import DirectoryImportContext
        return DirectoryImportContext

    def test_getLogger( self ):

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )
        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_readDataFile_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.readDataFile( FILENAME ), None )

    def test_readDataFile_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'
        self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.readDataFile( FILENAME ), printable )

    def test_readDataFile_subdir( self ):

        from string import printable

        FILENAME = 'subdir/nested.txt'
        self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.readDataFile( FILENAME ), printable )

    def test_getLastModified_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.getLastModified( FILENAME ), None )

    def test_getLastModified_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'
        fqpath = self._makeFile( FILENAME, printable )
        timestamp = os.path.getmtime( fqpath )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        lm = ctx.getLastModified( FILENAME )
        self.failUnless( isinstance( lm, DateTime ) )
        self.assertEqual( lm, timestamp )

    def test_getLastModified_subdir( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        fqpath = self._makeFile( FILENAME, printable )
        timestamp = os.path.getmtime( fqpath )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        lm = ctx.getLastModified( FILENAME )
        self.failUnless( isinstance( lm, DateTime ) )
        self.assertEqual( lm, timestamp )

    def test_getLastModified_directory( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        fqpath = self._makeFile( FILENAME, printable )
        path, file = os.path.split( fqpath )
        timestamp = os.path.getmtime( path )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        lm = ctx.getLastModified( SUBDIR )
        self.failUnless( isinstance( lm, DateTime ) )
        self.assertEqual( lm, timestamp )

    def test_isDirectory_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.isDirectory( FILENAME ), None )

    def test_isDirectory_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'
        fqpath = self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.isDirectory( FILENAME ), False )

    def test_isDirectory_nested( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        fqpath = self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.isDirectory( FILENAME ), False )

    def test_isDirectory_directory( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        fqpath = self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.isDirectory( SUBDIR ), True )

    def test_listDirectory_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.listDirectory( FILENAME ), None )

    def test_listDirectory_root( self ):

        from string import printable

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        FILENAME = 'simple.txt'
        self._makeFile( FILENAME, printable )

        self.assertEqual( len( ctx.listDirectory( None ) ), 1 )
        self.failUnless( FILENAME in ctx.listDirectory( None ) )

    def test_listDirectory_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'
        self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.listDirectory( FILENAME ), None )

    def test_listDirectory_nested( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        self.assertEqual( ctx.listDirectory( FILENAME ), None )

    def test_listDirectory_single( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 1 )
        self.failUnless( 'nested.txt' in names )

    def test_listDirectory_multiple( self ):

        from string import printable
        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        self._makeFile( FILENAME, printable )
        self._makeFile( os.path.join( SUBDIR, 'another.txt' ), 'ABC' )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 2 )
        self.failUnless( 'nested.txt' in names )
        self.failUnless( 'another.txt' in names )

    def test_listDirectory_skip_implicit( self ):

        from string import printable
        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        self._makeFile( FILENAME, printable )
        self._makeFile( os.path.join( SUBDIR, 'another.txt' ), 'ABC' )
        self._makeFile( os.path.join( SUBDIR, 'another.txt~' ), '123' )
        self._makeFile( os.path.join( SUBDIR, 'CVS/skip.txt' ), 'DEF' )
        self._makeFile( os.path.join( SUBDIR, '.svn/skip.txt' ), 'GHI' )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 2 )
        self.failUnless( 'nested.txt' in names )
        self.failUnless( 'another.txt' in names )
        self.failIf( 'another.txt~' in names )
        self.failIf( 'CVS' in names )
        self.failIf( '.svn' in names )

    def test_listDirectory_skip_explicit( self ):

        from string import printable
        SUBDIR = 'subdir'
        FILENAME = os.path.join( SUBDIR, 'nested.txt' )
        self._makeFile( FILENAME, printable )
        self._makeFile( os.path.join( SUBDIR, 'another.txt' ), 'ABC' )
        self._makeFile( os.path.join( SUBDIR, 'another.bak' ), '123' )
        self._makeFile( os.path.join( SUBDIR, 'CVS/skip.txt' ), 'DEF' )
        self._makeFile( os.path.join( SUBDIR, '.svn/skip.txt' ), 'GHI' )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        names = ctx.listDirectory(SUBDIR, skip=('nested.txt',),
                                  skip_suffixes=('.bak',))
        self.assertEqual( len( names ), 3 )
        self.failIf( 'nested.txt' in names )
        self.failIf( 'nested.bak' in names )
        self.failUnless( 'another.txt' in names )
        self.failUnless( 'CVS' in names )
        self.failUnless( '.svn' in names )


class DirectoryExportContextTests( FilesystemTestBase
                                 , ConformsToISetupContext
                                 , ConformsToIExportContext
                                 ):

    _PROFILE_PATH = '/tmp/ECTTexts'

    def _getTargetClass( self ):

        from Products.GenericSetup.context import DirectoryExportContext
        return DirectoryExportContext

    def test_getLogger( self ):

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )
        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_writeDataFile_simple( self ):

        from string import printable, digits
        FILENAME = 'simple.txt'
        fqname = self._makeFile( FILENAME, printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        ctx.writeDataFile( FILENAME, digits, 'text/plain' )

        self.assertEqual( open( fqname, 'rb' ).read(), digits )

    def test_writeDataFile_new_subdir( self ):

        from string import printable, digits
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        fqname = os.path.join( self._PROFILE_PATH, SUBDIR, FILENAME )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        ctx.writeDataFile( FILENAME, digits, 'text/plain', SUBDIR )

        self.assertEqual( open( fqname, 'rb' ).read(), digits )

    def test_writeDataFile_overwrite( self ):

        from string import printable, digits
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        fqname = self._makeFile( os.path.join( SUBDIR, FILENAME )
                               , printable )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        ctx.writeDataFile( FILENAME, digits, 'text/plain', SUBDIR )

        self.assertEqual( open( fqname, 'rb' ).read(), digits )

    def test_writeDataFile_existing_subdir( self ):

        from string import printable, digits
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        self._makeFile( os.path.join( SUBDIR, 'another.txt' ), printable )
        fqname = os.path.join( self._PROFILE_PATH, SUBDIR, FILENAME )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._makeOne( site, self._PROFILE_PATH )

        ctx.writeDataFile( FILENAME, digits, 'text/plain', SUBDIR )

        self.assertEqual( open( fqname, 'rb' ).read(), digits )


class TarballImportContextTests( SecurityRequestTest
                               , ConformsToISetupContext
                               , ConformsToIImportContext
                               ):

    def _getTargetClass( self ):

        from Products.GenericSetup.context import TarballImportContext
        return TarballImportContext

    def _makeOne( self, file_dict={}, mod_time=None, *args, **kw ):

        archive_stream = StringIO()
        archive = TarFile.open('test.tar.gz', 'w:gz', archive_stream)

        def _addOneMember(path, data, modtime):
            stream = StringIO(v)
            info = TarInfo(k)
            info.size = len(v)
            info.mtime = mod_time
            archive.addfile(info, stream)

        def _addMember(path, data, modtime):
            from tarfile import DIRTYPE
            elements = path.split('/')
            parents = filter(None, [elements[x] for x in range(len(elements))])
            for parent in parents:
                info = TarInfo()
                info.name = parent
                info.size = 0
                info.mtime = mod_time
                info.type = DIRTYPE
                archive.addfile(info, StringIO())
            _addOneMember(path, data, modtime)

        file_items = file_dict.items() or [('dummy', '')] # empty archive barfs

        if mod_time is None:
            mod_time = time.time()

        for k, v in file_items:
            _addMember(k, v, mod_time)

        archive.close()
        bits = archive_stream.getvalue()

        site = DummySite( 'site' ).__of__( self.root )
        site._setObject( 'setup_tool', Folder( 'setup_tool' ) )
        tool = site._getOb( 'setup_tool' )

        ctx = self._getTargetClass()( tool, bits, *args, **kw )

        return site, tool, ctx.__of__( tool )

    def test_getLogger( self ):

        site, tool, ctx = self._makeOne()
        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_ctorparms( self ):

        ENCODING = 'latin-1'
        site, tool, ctx = self._makeOne( encoding=ENCODING
                                       , should_purge=True
                                       )

        self.assertEqual( ctx.getEncoding(), ENCODING )
        self.assertEqual( ctx.shouldPurge(), True )

    def test_empty( self ):

        site, tool, ctx = self._makeOne()

        self.assertEqual( ctx.getSite(), site )
        self.assertEqual( ctx.getEncoding(), None )
        self.assertEqual( ctx.shouldPurge(), False )

        # These methods are all specified to return 'None' for non-existing
        # paths / entities
        self.assertEqual( ctx.isDirectory( 'nonesuch/path' ), None )
        self.assertEqual( ctx.listDirectory( 'nonesuch/path' ), None )

    def test_readDataFile_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne()

        self.assertEqual( ctx.readDataFile( FILENAME ), None )
        self.assertEqual( ctx.readDataFile( FILENAME, 'subdir' ), None )

    def test_readDataFile_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( { FILENAME: printable } )

        self.assertEqual( ctx.readDataFile( FILENAME ), printable )

    def test_readDataFile_subdir( self ):

        from string import printable

        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'

        site, tool, ctx = self._makeOne( { '%s/%s' % (SUBDIR, FILENAME):
                                            printable } )

        self.assertEqual( ctx.readDataFile( FILENAME, SUBDIR ), printable )

    def test_getLastModified_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne()

        self.assertEqual( ctx.getLastModified( FILENAME ), None )

    def test_getLastModified_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( { FILENAME : printable }
                                       , mod_time=WHEN )

        self.assertEqual( ctx.getLastModified( FILENAME ), WHEN )

    def test_getLastModified_subdir( self ):

        from string import printable

        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( { PATH: printable }
                                       , mod_time=WHEN )

        self.assertEqual( ctx.getLastModified( PATH ), WHEN )

    def test_getLastModified_directory( self ):

        from string import printable

        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( { PATH: printable }
                                       , mod_time=WHEN
                                       )

        self.assertEqual( ctx.getLastModified( SUBDIR ), WHEN )

    def test_isDirectory_nonesuch( self ):

        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne()

        self.assertEqual( ctx.isDirectory( FILENAME ), None )

    def test_isDirectory_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( { FILENAME: printable } )

        self.assertEqual( ctx.isDirectory( FILENAME ), False )

    def test_isDirectory_nested( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( { PATH: printable } )

        self.assertEqual( ctx.isDirectory( PATH ), False )

    def test_isDirectory_subdir( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( { PATH: printable } )

        self.assertEqual( ctx.isDirectory( SUBDIR ), True )

    def test_listDirectory_nonesuch( self ):

        SUBDIR = 'nonesuch/path'

        site, tool, ctx = self._makeOne()

        self.assertEqual( ctx.listDirectory( SUBDIR ), None )

    def test_listDirectory_root( self ):

        from string import printable

        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( { FILENAME: printable } )

        self.assertEqual( len( ctx.listDirectory( None ) ), 1 )
        self.failUnless( FILENAME in ctx.listDirectory( None ) )

    def test_listDirectory_simple( self ):

        from string import printable

        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( { FILENAME: printable } )

        self.assertEqual( ctx.listDirectory( FILENAME ), None )

    def test_listDirectory_nested( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( { PATH: printable } )

        self.assertEqual( ctx.listDirectory( PATH ), None )

    def test_listDirectory_single( self ):

        from string import printable

        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( { PATH: printable } )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 1 )
        self.failUnless( FILENAME in names )

    def test_listDirectory_multiple( self ):

        from string import printable, uppercase

        SUBDIR = 'subdir'
        FILENAME1 = 'nested.txt'
        PATH1 = '%s/%s' % ( SUBDIR, FILENAME1 )
        FILENAME2 = 'another.txt'
        PATH2 = '%s/%s' % ( SUBDIR, FILENAME2 )

        site, tool, ctx = self._makeOne( { PATH1: printable
                                         , PATH2: uppercase
                                         } )
                                             
        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 2 )
        self.failUnless( FILENAME1 in names )
        self.failUnless( FILENAME2 in names )

    def test_listDirectory_skip( self ):

        from string import printable, uppercase

        SUBDIR = 'subdir'
        FILENAME1 = 'nested.txt'
        PATH1 = '%s/%s' % ( SUBDIR, FILENAME1 )
        FILENAME2 = 'another.txt'
        PATH2 = '%s/%s' % ( SUBDIR, FILENAME2 )
        FILENAME3 = 'another.bak'
        PATH3 = '%s/%s' % ( SUBDIR, FILENAME3 )

        site, tool, ctx = self._makeOne( { PATH1: printable
                                         , PATH2: uppercase
                                         , PATH3: 'xyz'
                                         } )

        names = ctx.listDirectory(SUBDIR, skip=(FILENAME1,),
                                  skip_suffixes=('.bak',))
        self.assertEqual( len( names ), 1 )
        self.failIf( FILENAME1 in names )
        self.failUnless( FILENAME2 in names )
        self.failIf( FILENAME3 in names )


class TarballExportContextTests( FilesystemTestBase
                               , TarballTester
                               , ConformsToISetupContext
                               , ConformsToIExportContext
                               ):

    _PROFILE_PATH = '/tmp/TECT_tests'

    def _getTargetClass( self ):

        from Products.GenericSetup.context import TarballExportContext
        return TarballExportContext

    def test_getLogger( self ):

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._getTargetClass()( site )

        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_writeDataFile_simple( self ):

        from string import printable
        now = long( time.time() )

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._getTargetClass()( site )

        ctx.writeDataFile( 'foo.txt', printable, 'text/plain' )

        fileish = StringIO( ctx.getArchive() )

        self._verifyTarballContents( fileish, [ 'foo.txt' ], now )
        self._verifyTarballEntry( fileish, 'foo.txt', printable )

    def test_writeDataFile_multiple( self ):

        from string import printable
        from string import digits

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._getTargetClass()( site )

        ctx.writeDataFile( 'foo.txt', printable, 'text/plain' )
        ctx.writeDataFile( 'bar.txt', digits, 'text/plain' )

        fileish = StringIO( ctx.getArchive() )

        self._verifyTarballContents( fileish, [ 'foo.txt', 'bar.txt' ] )
        self._verifyTarballEntry( fileish, 'foo.txt', printable )
        self._verifyTarballEntry( fileish, 'bar.txt', digits )

    def test_writeDataFile_subdir( self ):

        from string import printable
        from string import digits

        site = DummySite( 'site' ).__of__( self.root )
        ctx = self._getTargetClass()( site )

        ctx.writeDataFile( 'foo.txt', printable, 'text/plain' )
        ctx.writeDataFile( 'bar/baz.txt', digits, 'text/plain' )

        fileish = StringIO( ctx.getArchive() )

        self._verifyTarballContents( fileish, [ 'foo.txt', 'bar/baz.txt' ] )
        self._verifyTarballEntry( fileish, 'foo.txt', printable )
        self._verifyTarballEntry( fileish, 'bar/baz.txt', digits )


class SnapshotExportContextTests( SecurityRequestTest
                                , ConformsToISetupContext
                                , ConformsToIExportContext
                                ):

    def _getTargetClass( self ):

        from Products.GenericSetup.context import SnapshotExportContext
        return SnapshotExportContext

    def _makeOne( self, *args, **kw ):

        return self._getTargetClass()( *args, **kw )

    def test_getLogger( self ):

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_writeDataFile_simple_image( self ):

        from OFS.Image import Image
        FILENAME = 'simple.txt'
        CONTENT_TYPE = 'image/png'
        png_filename = os.path.join( os.path.split( __file__ )[0]
                                   , 'simple.png' )
        png_file = open( png_filename, 'rb' )
        png_data = png_file.read()
        png_file.close()

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, png_data, CONTENT_TYPE )

        snapshot = tool.snapshots._getOb( 'simple' )

        self.assertEqual( len( snapshot.objectIds() ), 1 )
        self.failUnless( FILENAME in snapshot.objectIds() )

        fileobj = snapshot._getOb( FILENAME )

        self.assertEqual( fileobj.getId(), FILENAME )
        self.assertEqual( fileobj.meta_type, Image.meta_type )
        self.assertEqual( fileobj.getContentType(), CONTENT_TYPE )
        self.assertEqual( fileobj.data, png_data )

    def test_writeDataFile_simple_plain_text( self ):

        from string import digits
        from OFS.Image import File
        FILENAME = 'simple.txt'
        CONTENT_TYPE = 'text/plain'

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, digits, CONTENT_TYPE )

        snapshot = tool.snapshots._getOb( 'simple' )

        self.assertEqual( len( snapshot.objectIds() ), 1 )
        self.failUnless( FILENAME in snapshot.objectIds() )

        fileobj = snapshot._getOb( FILENAME )

        self.assertEqual( fileobj.getId(), FILENAME )
        self.assertEqual( fileobj.meta_type, File.meta_type )
        self.assertEqual( fileobj.getContentType(), CONTENT_TYPE )
        self.assertEqual( str( fileobj ), digits )

    def test_writeDataFile_simple_plain_text_unicode( self ):

        from string import digits
        from OFS.Image import File
        FILENAME = 'simple.txt'
        CONTENT_TYPE = 'text/plain'
        CONTENT = u'Unicode, with non-ASCII: %s.' % unichr(150)

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple', 'latin_1' )

        ctx.writeDataFile( FILENAME, CONTENT, CONTENT_TYPE )

        snapshot = tool.snapshots._getOb( 'simple' )

        self.assertEqual( len( snapshot.objectIds() ), 1 )
        self.failUnless( FILENAME in snapshot.objectIds() )

        fileobj = snapshot._getOb( FILENAME )

        self.assertEqual( fileobj.getId(), FILENAME )
        self.assertEqual( fileobj.meta_type, File.meta_type )
        self.assertEqual( fileobj.getContentType(), CONTENT_TYPE )
        saved = fileobj.manage_FTPget().decode('latin_1')
        self.assertEqual( saved, CONTENT )

    def test_writeDataFile_simple_xml( self ):

        from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
        FILENAME = 'simple.xml'
        CONTENT_TYPE = 'text/xml'
        _XML = """<?xml version="1.0"?><simple />"""

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, _XML, CONTENT_TYPE )

        snapshot = tool.snapshots._getOb( 'simple' )

        self.assertEqual( len( snapshot.objectIds() ), 1 )
        self.failUnless( FILENAME in snapshot.objectIds() )

        template = snapshot._getOb( FILENAME )

        self.assertEqual( template.getId(), FILENAME )
        self.assertEqual( template.meta_type, ZopePageTemplate.meta_type )
        self.assertEqual( template.read(), _XML )
        self.failIf( template.html() )

    def test_writeDataFile_unicode_xml( self ):

        from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
        FILENAME = 'simple.xml'
        CONTENT_TYPE = 'text/xml'
        _XML = u"""<?xml version="1.0"?><simple />"""

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, _XML, CONTENT_TYPE )

        snapshot = tool.snapshots._getOb( 'simple' )

        self.assertEqual( len( snapshot.objectIds() ), 1 )
        self.failUnless( FILENAME in snapshot.objectIds() )

        template = snapshot._getOb( FILENAME )

        self.assertEqual( template.getId(), FILENAME )
        self.assertEqual( template.meta_type, ZopePageTemplate.meta_type )
        self.assertEqual( template.read(), _XML )
        self.failIf( template.html() )

    def test_writeDataFile_subdir_dtml( self ):

        from OFS.DTMLDocument import DTMLDocument
        FILENAME = 'simple.dtml'
        CONTENT_TYPE = 'text/html'
        _HTML = """<html><body><h1>HTML</h1></body></html>"""

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, _HTML, CONTENT_TYPE, 'sub1' )

        snapshot = tool.snapshots._getOb( 'simple' )
        sub1 = snapshot._getOb( 'sub1' )

        self.assertEqual( len( sub1.objectIds() ), 1 )
        self.failUnless( FILENAME in sub1.objectIds() )

        template = sub1._getOb( FILENAME )

        self.assertEqual( template.getId(), FILENAME )
        self.assertEqual( template.meta_type, DTMLDocument.meta_type )
        self.assertEqual( template.read(), _HTML )

        ctx.writeDataFile( 'sub1/%s2' % FILENAME, _HTML, CONTENT_TYPE)
        self.assertEqual( len( sub1.objectIds() ), 2 )

    def test_writeDataFile_nested_subdirs_html( self ):

        from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
        FILENAME = 'simple.html'
        CONTENT_TYPE = 'text/html'
        _HTML = """<html><body><h1>HTML</h1></body></html>"""

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'simple' )

        ctx.writeDataFile( FILENAME, _HTML, CONTENT_TYPE, 'sub1/sub2' )

        snapshot = tool.snapshots._getOb( 'simple' )
        sub1 = snapshot._getOb( 'sub1' )
        sub2 = sub1._getOb( 'sub2' )

        self.assertEqual( len( sub2.objectIds() ), 1 )
        self.failUnless( FILENAME in sub2.objectIds() )

        template = sub2._getOb( FILENAME )

        self.assertEqual( template.getId(), FILENAME )
        self.assertEqual( template.meta_type, ZopePageTemplate.meta_type )
        self.assertEqual( template.read(), _HTML )
        self.failUnless( template.html() )

    def test_writeDataFile_multiple( self ):

        from string import printable
        from string import digits

        site = DummySite( 'site' ).__of__( self.root )
        site.setup_tool = DummyTool( 'setup_tool' )
        tool = site.setup_tool
        ctx = self._makeOne( tool, 'multiple' )

        ctx.writeDataFile( 'foo.txt', printable, 'text/plain' )
        ctx.writeDataFile( 'bar.txt', digits, 'text/plain' )

        snapshot = tool.snapshots._getOb( 'multiple' )

        self.assertEqual( len( snapshot.objectIds() ), 2 )

        for id in [ 'foo.txt', 'bar.txt' ]:
            self.failUnless( id in snapshot.objectIds() )


class SnapshotImportContextTests( SecurityRequestTest
                                , ConformsToISetupContext
                                , ConformsToIImportContext
                                ):

    def _getTargetClass( self ):

        from Products.GenericSetup.context import SnapshotImportContext
        return SnapshotImportContext

    def _makeOne( self, context_id, *args, **kw ):

        site = DummySite( 'site' ).__of__( self.root )
        site._setObject( 'setup_tool', Folder( 'setup_tool' ) )
        tool = site._getOb( 'setup_tool' )

        tool._setObject( 'snapshots', Folder( 'snapshots' ) )
        tool.snapshots._setObject( context_id, Folder( context_id ) )

        ctx = self._getTargetClass()( tool, context_id, *args, **kw )

        return site, tool, ctx.__of__( tool )

    def _makeFile( self
                 , tool
                 , snapshot_id
                 , filename
                 , contents
                 , content_type='text/plain'
                 , mod_time=None
                 , subdir=None
                 ):

        snapshots = tool._getOb( 'snapshots' )
        folder = snapshot = snapshots._getOb( snapshot_id )

        if subdir is not None:

            for element in subdir.split( '/' ):

                try:
                    folder = folder._getOb( element )
                except AttributeError:
                    folder._setObject( element, Folder( element ) )
                    folder = folder._getOb( element )

        file = File( filename, '', contents, content_type )
        folder._setObject( filename, file )

        if mod_time is not None:

            def __faux_mod_time():
                return mod_time

            folder.bobobase_modification_time = \
            file.bobobase_modification_time = __faux_mod_time

        return folder._getOb( filename )

    def test_getLogger( self ):

        SNAPSHOT_ID = 'note'
        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( len( ctx.listNotes() ), 0 )

        logger = ctx.getLogger('foo')
        logger.info('bar')

        self.assertEqual( len( ctx.listNotes() ), 1 )
        level, component, message = ctx.listNotes()[0]
        self.assertEqual( level, logging.INFO )
        self.assertEqual( component, 'foo' )
        self.assertEqual( message, 'bar' )

        ctx.clearNotes()
        self.assertEqual( len( ctx.listNotes() ), 0 )

    def test_ctorparms( self ):

        SNAPSHOT_ID = 'ctorparms'
        ENCODING = 'latin-1'
        site, tool, ctx = self._makeOne( SNAPSHOT_ID
                                       , encoding=ENCODING
                                       , should_purge=True
                                       )

        self.assertEqual( ctx.getEncoding(), ENCODING )
        self.assertEqual( ctx.shouldPurge(), True )

    def test_empty( self ):

        SNAPSHOT_ID = 'empty'
        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( ctx.getSite(), site )
        self.assertEqual( ctx.getEncoding(), None )
        self.assertEqual( ctx.shouldPurge(), False )

        # These methods are all specified to return 'None' for non-existing
        # paths / entities
        self.assertEqual( ctx.isDirectory( 'nonesuch/path' ), None )
        self.assertEqual( ctx.listDirectory( 'nonesuch/path' ), None )

    def test_readDataFile_nonesuch( self ):

        SNAPSHOT_ID = 'readDataFile_nonesuch'
        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( ctx.readDataFile( FILENAME ), None )
        self.assertEqual( ctx.readDataFile( FILENAME, 'subdir' ), None )

    def test_readDataFile_simple( self ):

        from string import printable

        SNAPSHOT_ID = 'readDataFile_simple'
        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable )

        self.assertEqual( ctx.readDataFile( FILENAME ), printable )

    def test_readDataFile_subdir( self ):

        from string import printable

        SNAPSHOT_ID = 'readDataFile_subdir'
        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                      , subdir=SUBDIR )

        self.assertEqual( ctx.readDataFile( FILENAME, SUBDIR ), printable )
        self.assertEqual( ctx.readDataFile( '%s/%s' % (SUBDIR, FILENAME) ),
                                            printable )

    def test_getLastModified_nonesuch( self ):

        SNAPSHOT_ID = 'getLastModified_nonesuch'
        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( ctx.getLastModified( FILENAME ), None )

    def test_getLastModified_simple( self ):

        from string import printable

        SNAPSHOT_ID = 'getLastModified_simple'
        FILENAME = 'simple.txt'
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , mod_time=WHEN )

        self.assertEqual( ctx.getLastModified( FILENAME ), WHEN )

    def test_getLastModified_subdir( self ):

        from string import printable

        SNAPSHOT_ID = 'getLastModified_subdir'
        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , mod_time=WHEN, subdir=SUBDIR )

        self.assertEqual( ctx.getLastModified( PATH ), WHEN )

    def test_getLastModified_directory( self ):

        from string import printable

        SNAPSHOT_ID = 'readDataFile_subdir'
        FILENAME = 'subdir.txt'
        SUBDIR = 'subdir'
        WHEN = DateTime( '2004-01-01T00:00:00Z' )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , mod_time=WHEN, subdir=SUBDIR )

        self.assertEqual( ctx.getLastModified( SUBDIR ), WHEN )

    def test_isDirectory_nonesuch( self ):

        SNAPSHOT_ID = 'isDirectory_nonesuch'
        FILENAME = 'nonesuch.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( ctx.isDirectory( FILENAME ), None )

    def test_isDirectory_simple( self ):

        from string import printable

        SNAPSHOT_ID = 'isDirectory_simple'
        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable )

        self.assertEqual( ctx.isDirectory( FILENAME ), False )

    def test_isDirectory_nested( self ):

        from string import printable

        SNAPSHOT_ID = 'isDirectory_nested'
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , subdir=SUBDIR )

        self.assertEqual( ctx.isDirectory( PATH ), False )

    def test_isDirectory_subdir( self ):

        from string import printable

        SNAPSHOT_ID = 'isDirectory_subdir'
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , subdir=SUBDIR )

        self.assertEqual( ctx.isDirectory( SUBDIR ), True )

    def test_listDirectory_nonesuch( self ):

        SNAPSHOT_ID = 'listDirectory_nonesuch'
        SUBDIR = 'nonesuch/path'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )

        self.assertEqual( ctx.listDirectory( SUBDIR ), None )

    def test_listDirectory_root( self ):

        from string import printable

        SNAPSHOT_ID = 'listDirectory_root'
        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable )

        self.assertEqual( len( ctx.listDirectory( None ) ), 1 )
        self.failUnless( FILENAME in ctx.listDirectory( None ) )

    def test_listDirectory_simple( self ):

        from string import printable

        SNAPSHOT_ID = 'listDirectory_simple'
        FILENAME = 'simple.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable )

        self.assertEqual( ctx.listDirectory( FILENAME ), None )

    def test_listDirectory_nested( self ):

        from string import printable

        SNAPSHOT_ID = 'listDirectory_nested'
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'
        PATH = '%s/%s' % ( SUBDIR, FILENAME )

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , subdir=SUBDIR )

        self.assertEqual( ctx.listDirectory( PATH ), None )

    def test_listDirectory_single( self ):

        from string import printable

        SNAPSHOT_ID = 'listDirectory_nested'
        SUBDIR = 'subdir'
        FILENAME = 'nested.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file = self._makeFile( tool, SNAPSHOT_ID, FILENAME, printable
                             , subdir=SUBDIR )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 1 )
        self.failUnless( FILENAME in names )

    def test_listDirectory_multiple( self ):

        from string import printable, uppercase

        SNAPSHOT_ID = 'listDirectory_nested'
        SUBDIR = 'subdir'
        FILENAME1 = 'nested.txt'
        FILENAME2 = 'another.txt'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file1 = self._makeFile( tool, SNAPSHOT_ID, FILENAME1, printable
                              , subdir=SUBDIR )
        file2 = self._makeFile( tool, SNAPSHOT_ID, FILENAME2, uppercase
                              , subdir=SUBDIR )

        names = ctx.listDirectory( SUBDIR )
        self.assertEqual( len( names ), 2 )
        self.failUnless( FILENAME1 in names )
        self.failUnless( FILENAME2 in names )

    def test_listDirectory_skip( self ):

        from string import printable, uppercase

        SNAPSHOT_ID = 'listDirectory_nested'
        SUBDIR = 'subdir'
        FILENAME1 = 'nested.txt'
        FILENAME2 = 'another.txt'
        FILENAME3 = 'another.bak'

        site, tool, ctx = self._makeOne( SNAPSHOT_ID )
        file1 = self._makeFile( tool, SNAPSHOT_ID, FILENAME1, printable
                              , subdir=SUBDIR )
        file2 = self._makeFile( tool, SNAPSHOT_ID, FILENAME2, uppercase
                              , subdir=SUBDIR )
        file3 = self._makeFile( tool, SNAPSHOT_ID, FILENAME3, 'abc'
                              , subdir=SUBDIR )

        names = ctx.listDirectory(SUBDIR, skip=(FILENAME1,),
                                  skip_suffixes=('.bak',))
        self.assertEqual( len( names ), 1 )
        self.failIf( FILENAME1 in names )
        self.failUnless( FILENAME2 in names )
        self.failIf( FILENAME3 in names )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( DirectoryImportContextTests ),
        unittest.makeSuite( DirectoryExportContextTests ),
        unittest.makeSuite( TarballImportContextTests ),
        unittest.makeSuite( TarballExportContextTests ),
        unittest.makeSuite( SnapshotExportContextTests ),
        unittest.makeSuite( SnapshotImportContextTests ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
