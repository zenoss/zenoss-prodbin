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
""" Diff utilities for comparing configurations.

$Id: differ.py 41383 2006-01-20 13:49:16Z efge $
"""

from difflib import unified_diff
import re

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from interfaces import SKIPPED_FILES

BLANKS_REGEX = re.compile( r'^\s*$' )

def unidiff( a
           , b
           , filename_a='original'
           , timestamp_a=None
           , filename_b='modified'
           , timestamp_b=None
           , ignore_blanks=False
           ):
    r"""Compare two sequences of lines; generate the resulting delta.

    Each sequence must contain individual single-line strings
    ending with newlines. Such sequences can be obtained from the
    `readlines()` method of file-like objects.  The delta
    generated also consists of newline-terminated strings, ready
    to be printed as-is via the writeline() method of a file-like
    object.

    Note that the last line of a file may *not* have a newline;
    this is reported in the same way that GNU diff reports this.
    *This method only supports UNIX line ending conventions.*

        filename_a and filename_b are used to generate the header,
        allowing other tools to determine what 'files' were used
        to generate this output.

        timestamp_a and timestamp_b, when supplied, are expected
        to be last-modified timestamps to be inserted in the
        header, as floating point values since the epoch.

    Example:

    >>> print ''.join(UniDiffer().compare(
    ...     'one\ntwo\nthree\n'.splitlines(1),
    ...     'ore\ntree\nemu\n'.splitlines(1))),
    +++ original
    --- modified
    @@ -1,3 +1,3 @@
    -one
    +ore
    -two
    -three
    +tree
    +emu
    """
    if isinstance( a, basestring ):
        a = a.splitlines()

    if isinstance( b, basestring ):
        b = b.splitlines()

    if ignore_blanks:
        a = [ x for x in a if not BLANKS_REGEX.match( x ) ]
        b = [ x for x in b if not BLANKS_REGEX.match( x ) ]

    return unified_diff( a
                       , b
                       , filename_a
                       , filename_b
                       , timestamp_a
                       , timestamp_b
                       , lineterm=""
                       )

class ConfigDiff:

    security = ClassSecurityInfo()

    def __init__( self
                , lhs
                , rhs
                , missing_as_empty=False
                , ignore_blanks=False
                , skip=SKIPPED_FILES
                ):
        self._lhs = lhs
        self._rhs = rhs
        self._missing_as_empty = missing_as_empty
        self._ignore_blanks=ignore_blanks
        self._skip = skip

    security.declarePrivate( 'compareDirectories' )
    def compareDirectories( self, subdir=None ):

        lhs_files = self._lhs.listDirectory( subdir, self._skip )
        if lhs_files is None:
            lhs_files = []

        rhs_files = self._rhs.listDirectory( subdir, self._skip )
        if rhs_files is None:
            rhs_files = []

        added = [ f for f in rhs_files if f not in lhs_files ]
        removed = [ f for f in lhs_files if f not in rhs_files ]
        all_files = lhs_files + added
        all_files.sort()

        result = []

        for filename in all_files:

            if subdir is None:
                pathname = filename
            else:
                pathname = '%s/%s' % ( subdir, filename )

            if filename not in added:
                isDirectory = self._lhs.isDirectory( pathname )
            else:
                isDirectory = self._rhs.isDirectory( pathname )

            if not self._missing_as_empty and filename in removed:

                if isDirectory:
                    result.append( '** Directory %s removed\n' % pathname )
                    result.extend( self.compareDirectories( pathname ) )
                else:
                    result.append( '** File %s removed\n' % pathname )

            elif not self._missing_as_empty and filename in added:

                if isDirectory:
                    result.append( '** Directory %s added\n' % pathname )
                    result.extend( self.compareDirectories( pathname ) )
                else:
                    result.append( '** File %s added\n' % pathname )

            elif isDirectory:

                result.extend( self.compareDirectories( pathname ) )

                if ( filename not in added + removed and
                    not self._rhs.isDirectory( pathname ) ):

                    result.append( '** Directory %s replaced with a file of '
                                   'the same name\n' % pathname )

                    if self._missing_as_empty:
                        result.extend( self.compareFiles( filename, subdir ) )
            else:
                if ( filename not in added + removed and
                     self._rhs.isDirectory( pathname ) ):

                    result.append( '** File %s replaced with a directory of '
                                   'the same name\n' % pathname )

                    if self._missing_as_empty:
                        result.extend( self.compareFiles( filename, subdir ) )

                    result.extend( self.compareDirectories( pathname ) )
                else:
                    result.extend( self.compareFiles( filename, subdir ) )

        return result

    security.declarePrivate( 'compareFiles' )
    def compareFiles( self, filename, subdir=None ):

        if subdir is None:
            path = filename
        else:
            path = '%s/%s' % ( subdir, filename )

        lhs_file = self._lhs.readDataFile( filename, subdir )
        lhs_time = self._lhs.getLastModified( path )

        if lhs_file is None:
            assert self._missing_as_empty
            lhs_file = ''
            lhs_time = 0

        rhs_file = self._rhs.readDataFile( filename, subdir )
        rhs_time = self._rhs.getLastModified( path )

        if rhs_file is None:
            assert self._missing_as_empty
            rhs_file = ''
            rhs_time = 0

        if lhs_file == rhs_file:
            diff_lines = []
        else:
            diff_lines = unidiff( lhs_file
                                , rhs_file
                                , filename_a=path
                                , timestamp_a=lhs_time
                                , filename_b=path
                                , timestamp_b=rhs_time
                                , ignore_blanks=self._ignore_blanks
                                )
            diff_lines = list( diff_lines ) # generator

        if len( diff_lines ) == 0: # No *real* difference found
            return []

        diff_lines.insert( 0, 'Index: %s' % path )
        diff_lines.insert( 1, '=' * 67 )

        return diff_lines

    security.declarePrivate( 'compare' )
    def compare( self ):
        return '\n'.join( self.compareDirectories() )

InitializeClass( ConfigDiff )
