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
""" Unit tests for differ module.

$Id: test_differ.py 68488 2006-06-04 17:22:57Z yuppie $
"""

import unittest
import Testing

from OFS.Folder import Folder
from OFS.Image import File

from DateTime.DateTime import DateTime

from common import SecurityRequestTest


class DummySite( Folder ):

    pass


class Test_unidiff( unittest.TestCase ):

    def test_unidiff_both_text( self ):

        from Products.GenericSetup.differ import unidiff

        diff_lines = unidiff( ONE_FOUR, ZERO_FOUR )
        diff_text = '\n'.join( diff_lines )
        self.assertEqual( diff_text, DIFF_TEXT )

    def test_unidiff_both_lines( self ):

        from Products.GenericSetup.differ import unidiff

        diff_lines = unidiff( ONE_FOUR.splitlines(), ZERO_FOUR.splitlines() )
        diff_text = '\n'.join( diff_lines )
        self.assertEqual( diff_text, DIFF_TEXT )

    def test_unidiff_mixed( self ):

        from Products.GenericSetup.differ import unidiff

        diff_lines = unidiff( ONE_FOUR, ZERO_FOUR.splitlines() )
        diff_text = '\n'.join( diff_lines )
        self.assertEqual( diff_text, DIFF_TEXT )

    def test_unidiff_ignore_blanks( self ):

        from Products.GenericSetup.differ import unidiff

        double_spaced = ONE_FOUR.replace( '\n', '\n\n' )
        diff_lines = unidiff( double_spaced
                            , ZERO_FOUR.splitlines()
                            , ignore_blanks=True
                            )

        diff_text = '\n'.join( diff_lines )
        self.assertEqual( diff_text, DIFF_TEXT )

ZERO_FOUR = """\
zero
one
tree
four
"""

ONE_FOUR = """\
one
two
three
four
"""

DIFF_TEXT = """\
--- original None
+++ modified None
@@ -1,4 +1,4 @@
+zero
 one
-two
-three
+tree
 four\
"""

class ConfigDiffTests( SecurityRequestTest ):

    site = None
    tool = None

    def _getTargetClass( self ):

        from Products.GenericSetup.differ import ConfigDiff
        return ConfigDiff

    def _makeOne( self, lhs, rhs, *args, **kw ):

        return self._getTargetClass()( lhs, rhs, *args, **kw )

    def _makeSite( self ):

        if self.site is not None:
            return

        site = self.site = DummySite( 'site' ).__of__( self.root )
        site._setObject( 'setup_tool', Folder( 'setup_tool' ) )
        self.tool = tool = site._getOb( 'setup_tool' )

        tool._setObject( 'snapshots', Folder( 'snapshots' ) )

    def _makeContext( self, context_id ):

        from Products.GenericSetup.context import SnapshotImportContext

        self._makeSite()

        if context_id not in self.tool.snapshots.objectIds():
            self.tool.snapshots._setObject( context_id, Folder( context_id ) )

        ctx = SnapshotImportContext( self.tool, context_id )

        return ctx.__of__( self.tool )

    def _makeDirectory( self, snapshot_id, subdir ):

        self._makeSite()
        folder = self.tool.snapshots._getOb( snapshot_id )

        for element in subdir.split( '/' ):

            try:
                folder = folder._getOb( element )
            except AttributeError:
                folder._setObject( element, Folder( element ) )
                folder = folder._getOb( element )

        return folder

    def _makeFile( self
                 , snapshot_id
                 , filename
                 , contents
                 , content_type='text/plain'
                 , mod_time=None
                 , subdir=None
                 ):

        self._makeSite()
        snapshots = self.tool.snapshots
        snapshot = snapshots._getOb( snapshot_id )

        if subdir is not None:
            folder = self._makeDirectory( snapshot_id, subdir )
        else:
            folder = snapshot

        file = File( filename, '', contents, content_type )
        folder._setObject( filename, file )

        if mod_time is not None:

            def __faux_mod_time():
                return mod_time

            folder.bobobase_modification_time = \
            file.bobobase_modification_time = __faux_mod_time

        return folder._getOb( filename )

    def test_compare_empties( self ):

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, '' )

    def test_compare_identical( self ):

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF' )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF' )
        self._makeFile( 'rhs', 'again.txt', 'GHIJKL', subdir='sub' )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, '' )

    def test_compare_changed_file( self ):

        BEFORE = DateTime( '2004-01-01T00:00:00Z' )
        AFTER = DateTime( '2004-02-29T23:59:59Z' )

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ', mod_time=BEFORE )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nQRST', mod_time=AFTER )
        self._makeFile( 'rhs', 'again.txt', 'GHIJKL', subdir='sub' )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, TEST_TXT_DIFFS % ( BEFORE, AFTER ) )

    def test_compare_changed_file_ignore_blanks( self ):

        BEFORE = DateTime( '2004-01-01T00:00:00Z' )
        AFTER = DateTime( '2004-02-29T23:59:59Z' )

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ', mod_time=BEFORE )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\n\n\nWXYZ', mod_time=AFTER )

        cd = self._makeOne( lhs, rhs, ignore_blanks=True )

        diffs = cd.compare()

        self.assertEqual( diffs, '' )

    def test_compare_changed_file_explicit_skip( self ):

        BEFORE = DateTime( '2004-01-01T00:00:00Z' )
        AFTER = DateTime( '2004-02-29T23:59:59Z' )

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ', subdir='skipme'
                      , mod_time=BEFORE )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nQRST', subdir='skipme'
                      , mod_time=AFTER )
        self._makeFile( 'rhs', 'again.txt', 'GHIJKL', subdir='sub' )

        cd = self._makeOne( lhs, rhs, skip=[ 'skipme' ] )

        diffs = cd.compare()

        self.assertEqual( diffs, '' )

    def test_compare_changed_file_implicit_skip( self ):

        BEFORE = DateTime( '2004-01-01T00:00:00Z' )
        AFTER = DateTime( '2004-02-29T23:59:59Z' )

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ', subdir='CVS'
                      , mod_time=BEFORE )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='.svn'
                      , mod_time=BEFORE )

        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nQRST', subdir='CVS'
                      , mod_time=AFTER )
        self._makeFile( 'rhs', 'again.txt', 'MNOPQR', subdir='.svn'
                      , mod_time=AFTER )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, '' )

    def test_compare_added_file_no_missing_as_empty( self ):

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeDirectory( 'lhs', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeFile( 'rhs', 'again.txt', 'GHIJKL', subdir='sub' )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, ADDED_FILE_DIFFS_NO_MAE )

    def test_compare_added_file_missing_as_empty( self ):

        AFTER = DateTime( '2004-02-29T23:59:59Z' )
        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeDirectory( 'lhs', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeFile( 'rhs', 'again.txt', 'GHIJKL', subdir='sub'
                      , mod_time=AFTER )

        cd = self._makeOne( lhs, rhs, missing_as_empty=True )

        diffs = cd.compare()

        self.assertEqual( diffs, ADDED_FILE_DIFFS_MAE % AFTER )

    def test_compare_removed_file_no_missing_as_empty( self ):

        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='sub' )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeDirectory( 'rhs', subdir='sub' )

        cd = self._makeOne( lhs, rhs )

        diffs = cd.compare()

        self.assertEqual( diffs, REMOVED_FILE_DIFFS_NO_MAE )

    def test_compare_removed_file_missing_as_empty( self ):

        BEFORE = DateTime( '2004-01-01T00:00:00Z' )
        lhs = self._makeContext( 'lhs' )
        rhs = self._makeContext( 'rhs' )

        self._makeFile( 'lhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeFile( 'lhs', 'again.txt', 'GHIJKL', subdir='sub'
                      , mod_time=BEFORE )
        self._makeFile( 'rhs', 'test.txt', 'ABCDEF\nWXYZ' )
        self._makeDirectory( 'rhs', subdir='sub' )

        cd = self._makeOne( lhs, rhs, missing_as_empty=True )

        diffs = cd.compare()

        self.assertEqual( diffs, REMOVED_FILE_DIFFS_MAE % BEFORE )


TEST_TXT_DIFFS = """\
Index: test.txt
===================================================================
--- test.txt %s
+++ test.txt %s
@@ -1,2 +1,2 @@
 ABCDEF
-WXYZ
+QRST\
"""

ADDED_FILE_DIFFS_NO_MAE = """\
** File sub/again.txt added
"""

ADDED_FILE_DIFFS_MAE = """\
Index: sub/again.txt
===================================================================
--- sub/again.txt 0
+++ sub/again.txt %s
@@ -1,0 +1,1 @@
+GHIJKL\
"""

REMOVED_FILE_DIFFS_NO_MAE = """\
** File sub/again.txt removed
"""

REMOVED_FILE_DIFFS_MAE = """\
Index: sub/again.txt
===================================================================
--- sub/again.txt %s
+++ sub/again.txt 0
@@ -1,1 +1,0 @@
-GHIJKL\
"""


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_unidiff),
        unittest.makeSuite(ConfigDiffTests),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
