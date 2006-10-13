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
""" GenericSetup product:  unit test utilities.

$Id: common.py 69230 2006-07-21 10:44:38Z yuppie $
"""

import os
import shutil
from tarfile import TarFile

from Acquisition import Implicit
from Testing.ZopeTestCase import ZopeTestCase
from zope.interface import implements

from Products.Five import zcml
from Products.GenericSetup.interfaces import IExportContext
from Products.GenericSetup.interfaces import IImportContext
from Products.GenericSetup.testing import DummyLogger


class OmnipotentUser(Implicit):
    """ Omnipotent User for unit testing purposes.
    """
    def getId(self):
        return 'all_powerful_Oz'

    getUserName = getId

    def getRoles(self):
        return ('Manager',)

    def allowed(self, object, object_roles=None):
        return 1

    def getRolesInContext(self, object):
        return ('Manager',)


class SecurityRequestTest(ZopeTestCase):

    def setUp(self):
        import Products
        from AccessControl.SecurityManagement import newSecurityManager
        ZopeTestCase.setUp(self)
        try:
            import zope.traversing
            zcml.load_config('meta.zcml', Products.Five)
            zcml.load_config('traversing.zcml', Products.Five)
        except ImportError:
            # BBB: for Zope 2.9
            pass
        self.root = self.app
        newSecurityManager(None, OmnipotentUser().__of__(self.app.acl_users))

    def tearDown(self):
        from AccessControl.SecurityManagement import noSecurityManager
        noSecurityManager()
        ZopeTestCase.tearDown(self)
        try:
            from zope.testing.cleanup import cleanUp
            cleanUp()
        except ImportError:
            # BBB: for Zope 2.8
            pass


class DOMComparator:

    def _compareDOM( self, found_text, expected_text, debug=False ):

        found_lines = [ x.strip() for x in found_text.splitlines() ]
        found_text = '\n'.join( filter( None, found_lines ) )

        expected_lines = [ x.strip() for x in expected_text.splitlines() ]
        expected_text = '\n'.join( filter( None, expected_lines ) )

        from xml.dom.minidom import parseString
        found = parseString( found_text )
        expected = parseString( expected_text )
        fxml = found.toxml()
        exml = expected.toxml()

        if fxml != exml:

            if debug:
                zipped = zip( fxml, exml )
                diff = [ ( i, zipped[i][0], zipped[i][1] )
                        for i in range( len( zipped ) )
                        if zipped[i][0] != zipped[i][1]
                    ]
                import pdb; pdb.set_trace()

            print 'Found:'
            print fxml
            print
            print 'Expected:'
            print exml
            print

        self.assertEqual( found.toxml(), expected.toxml() )


class BaseRegistryTests( SecurityRequestTest, DOMComparator ):

    def _makeOne( self, *args, **kw ):

        # Derived classes must implement _getTargetClass
        return self._getTargetClass()( *args, **kw )


def _clearTestDirectory( root_path ):

    if os.path.exists( root_path ):
        shutil.rmtree( root_path )

def _makeTestFile( filename, root_path, contents ):

    path, filename = os.path.split( filename )

    subdir = os.path.join( root_path, path )

    if not os.path.exists( subdir ):
        os.makedirs( subdir )

    fqpath = os.path.join( subdir, filename )

    file = open( fqpath, 'wb' )
    file.write( contents )
    file.close()
    return fqpath


class FilesystemTestBase( SecurityRequestTest ):

    def _makeOne( self, *args, **kw ):

        return self._getTargetClass()( *args, **kw )

    def setUp( self ):

        SecurityRequestTest.setUp( self )
        self._clearTempDir()

    def tearDown( self ):

        self._clearTempDir()
        SecurityRequestTest.tearDown( self )

    def _clearTempDir( self ):

        _clearTestDirectory( self._PROFILE_PATH )

    def _makeFile( self, filename, contents ):

        return _makeTestFile( filename, self._PROFILE_PATH, contents )


class TarballTester( DOMComparator ):

    def _verifyTarballContents( self, fileish, toc_list, when=None ):

        fileish.seek( 0L )
        tarfile = TarFile.open( 'foo.tar.gz', fileobj=fileish, mode='r:gz' )
        items = tarfile.getnames()
        items.sort()
        toc_list.sort()

        self.assertEqual( len( items ), len( toc_list ) )
        for i in range( len( items ) ):
            self.assertEqual( items[ i ], toc_list[ i ] )

        if when is not None:
            for tarinfo in tarfile:
                self.failIf( tarinfo.mtime < when )

    def _verifyTarballEntry( self, fileish, entry_name, data ):

        fileish.seek( 0L )
        tarfile = TarFile.open( 'foo.tar.gz', fileobj=fileish, mode='r:gz' )
        extract = tarfile.extractfile( entry_name )
        found = extract.read()
        self.assertEqual( found, data )

    def _verifyTarballEntryXML( self, fileish, entry_name, data ):

        fileish.seek( 0L )
        tarfile = TarFile.open( 'foo.tar.gz', fileobj=fileish, mode='r:gz' )
        extract = tarfile.extractfile( entry_name )
        found = extract.read()
        self._compareDOM( found, data )


class DummyExportContext:

    implements(IExportContext)

    def __init__( self, site, tool=None ):
        self._site = site
        self._tool = tool
        self._wrote = []
        self._notes = []

    def getSite( self ):
        return self._site

    def getSetupTool( self ):
        return self._tool

    def getLogger(self, name):
        return DummyLogger(name, self._notes)

    def writeDataFile( self, filename, text, content_type, subdir=None ):
        if subdir is not None:
            filename = '%s/%s' % ( subdir, filename )
        self._wrote.append( ( filename, text, content_type ) )


class DummyImportContext:

    implements(IImportContext)

    def __init__( self, site, purge=True, encoding=None, tool=None ):
        self._site = site
        self._tool = tool
        self._purge = purge
        self._encoding = encoding
        self._files = {}
        self._notes = []

    def getSite( self ):
        return self._site

    def getSetupTool( self ):
        return self._tool

    def getEncoding( self ):
        return self._encoding

    def getLogger(self, name):
        return DummyLogger(name, self._notes)

    def readDataFile( self, filename, subdir=None ):

        if subdir is not None:
            filename = '/'.join( (subdir, filename) )

        return self._files.get( filename )

    def shouldPurge( self ):

        return self._purge


def dummy_handler( context ):

    pass
