from unittest import TestSuite, makeSuite, main
from os.path import join

import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from OFS.Folder import Folder

from Products.CMFCore.FSZSQLMethod import FSZSQLMethod
from Products.CMFCore.FSMetadata import FSMetadata
from Products.CMFCore.tests.base.testcase import FSDVTest
from Products.CMFCore.tests.base.testcase import SecurityTest

class FSZSQLMaker(FSDVTest):

    def _makeOne( self, id, filename ):
        path = join(self.skin_path_name, filename)
        metadata = FSMetadata(path)
        metadata.read()
        return FSZSQLMethod( id, path, properties=metadata.getProperties() )

class FSZSQLMethodTests( FSDVTest ):

    def setUp(self):
        FSDVTest.setUp(self)
        self._registerDirectory(self)

    def test_initialization(self):
        zsql = self.ob.fake_skin.testsql
        self.assertEqual(zsql.title, 'This is a title')
        self.assertEqual(zsql.connection_id, 'testconn')
        self.assertEqual(zsql.arguments_src, 'id')
        self.assertEqual(zsql.max_rows_, 1000)
        self.assertEqual(zsql.max_cache_, 100)
        self.assertEqual(zsql.cache_time_, 10)
        self.assertEqual(zsql.class_name_, 'MyRecord')
        self.assertEqual(zsql.class_file_, 'CMFCore.TestRecord')
        self.assertEqual(zsql.connection_hook, 'MyHook')
        self.failIf(zsql.allow_simple_one_argument_traversal is None)


class FSZSQLMethodCustomizationTests(SecurityTest, FSZSQLMaker):

    def setUp( self ):
        FSZSQLMaker.setUp(self)
        SecurityTest.setUp( self )

        self.root._setObject( 'portal_skins', Folder( 'portal_skins' ) )
        self.skins = self.root.portal_skins

        self.skins._setObject( 'custom', Folder( 'custom' ) )
        self.custom = self.skins.custom

        self.skins._setObject( 'fsdir', Folder( 'fsdir' ) )
        self.fsdir = self.skins.fsdir

        self.fsdir._setObject( 'testsql'
                             , self._makeOne( 'testsql', 'testsql.zsql' ) )

        self.fsZSQL = self.fsdir.testsql

    def tearDown(self):
        SecurityTest.tearDown(self)
        FSZSQLMaker.tearDown(self)

    def test_customize( self ):

        self.fsZSQL.manage_doCustomize( folder_path='custom' )

        self.assertEqual( len( self.custom.objectIds() ), 1 )
        self.failUnless( 'testsql' in self.custom.objectIds() )   

    def test_customize_properties(self):
        # Make sure all properties are coming across
        self.fsZSQL.manage_doCustomize( folder_path='custom' )
        zsql = self.custom.testsql

        self.assertEqual(zsql.title, 'This is a title')
        self.assertEqual(zsql.connection_id, 'testconn')
        self.assertEqual(zsql.arguments_src, 'id')
        self.assertEqual(zsql.max_rows_, 1000)
        self.assertEqual(zsql.max_cache_, 100)
        self.assertEqual(zsql.cache_time_, 10)
        self.assertEqual(zsql.class_name_, 'MyRecord')
        self.assertEqual(zsql.class_file_, 'CMFCore.TestRecord')
        self.assertEqual(zsql.connection_hook, 'MyHook')
        self.failIf(zsql.allow_simple_one_argument_traversal is None)


def test_suite():
    return TestSuite((
        makeSuite(FSZSQLMethodTests),
        makeSuite(FSZSQLMethodCustomizationTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
