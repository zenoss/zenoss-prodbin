from unittest import TestSuite, makeSuite, main
import Testing
try:
    import Zope2
except ImportError: # BBB: for Zope 2.7
    import Zope as Zope2
Zope2.startup()

from os.path import join

from OFS.Folder import Folder

from Products.CMFCore.FSPropertiesObject import FSPropertiesObject
from Products.CMFCore.tests.base.testcase import FSDVTest
from Products.CMFCore.tests.base.testcase import SecurityTest


class FSPOMaker(FSDVTest):

    def _makeOne( self, id, filename ):
        path = join(self.skin_path_name, filename)
        return FSPropertiesObject( id, path ) 


class FSPropertiesObjectCustomizationTests(SecurityTest, FSPOMaker):

    def setUp( self ):
        FSPOMaker.setUp(self)
        SecurityTest.setUp( self )

        self.root._setObject( 'portal_skins', Folder( 'portal_skins' ) )
        self.skins = self.root.portal_skins

        self.skins._setObject( 'custom', Folder( 'custom' ) )
        self.custom = self.skins.custom

        self.skins._setObject( 'fsdir', Folder( 'fsdir' ) )
        self.fsdir = self.skins.fsdir

        self.fsdir._setObject( 'test_props'
                             , self._makeOne( 'test_props', 'test_props.props' ) )

        self.fsPO = self.fsdir.test_props

    def tearDown(self):
        SecurityTest.tearDown(self)
        FSPOMaker.tearDown(self)

    def test_customize( self ):

        self.fsPO.manage_doCustomize( folder_path='custom' )

        self.assertEqual( len( self.custom.objectIds() ), 1 )
        self.failUnless( 'test_props' in self.custom.objectIds() )  


def test_suite():
    return TestSuite((
        makeSuite(FSPropertiesObjectCustomizationTests),
        ))

if __name__ == '__main__':
    main(defaultTest='test_suite')
