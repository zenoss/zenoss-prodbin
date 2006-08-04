""" Unit test for CMFBTreeFolder

$Id: test_CMFBTreeFolder.py 37144 2005-07-13 02:31:01Z tseaver $
"""

import unittest

class CMFBTreeFolderTests(unittest.TestCase):

    def _getTargetClass(self):

        from Products.CMFCore.CMFBTreeFolder import CMFBTreeFolder
        return CMFBTreeFolder

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id, *args, **kw )

    def test_empty( self ):

        empty = self._makeOne()
        self.assertEqual( len( empty.objectIds() ), 0 )

    def test___module_aliases__( self ):
 
        # This test will *fail* on Zope 2.8.0, because it (erroneously)
        # included CMFBTreeFolder in the core BTreeFolder2 product.
        from Products.BTreeFolder2.CMFBTreeFolder \
            import CMFBTreeFolder as BBB

        self.failUnless( BBB is self._getTargetClass() )
        

def test_suite():
    suite = unittest.TestSuite()
    # Don't test CMFBTreeFolder unless the underlying support is present.
    try:
        import Products.BTreeFolder2
    except ImportError:
        pass
    else:
        suite.addTest( unittest.makeSuite( CMFBTreeFolderTests ) )
    return suite

if __name__ == '__main__':
    unittest.main( defaultTest='test_suite' )
