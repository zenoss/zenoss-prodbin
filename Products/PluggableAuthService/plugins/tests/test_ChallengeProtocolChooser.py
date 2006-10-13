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
""" Unit tests for ChallengeProtocolChooser

$Id: test_ChallengeProtocolChooser.py 39343 2005-08-17 20:53:14Z sidnei $
"""
import unittest

from Products.PluggableAuthService.tests.conformance \
    import IChallengeProtocolChooser_conformance

class ChallengeProtocolChooser( unittest.TestCase
                                , IChallengeProtocolChooser_conformance 
                              ):


    def _getTargetClass( self ):

        from Products.PluggableAuthService.plugins.ChallengeProtocolChooser \
            import ChallengeProtocolChooser

        return ChallengeProtocolChooser

    def _makeOne( self, id='test', *args, **kw ):

        return self._getTargetClass()( id, *args, **kw )


if __name__ == "__main__":
    unittest.main()
        
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( ChallengeProtocolChooser ),
        ))
        
