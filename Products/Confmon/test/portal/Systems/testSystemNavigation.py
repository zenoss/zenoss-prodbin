#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class SystemListTest(unittest.TestCase):
    '''make sure that Confmon is in the systems dir'''
    systems = (makerequest.makerequest(Zope.app())).dmd.Systems.index_html

    def testHasConfmon(self):
        '''is confmon here?'''
        self.assertEqual(
            self.systems().find('"/dmd/Systems/Confmon"') != -1, 1)

class SubSystemListTest(unittest.TestCase):
    '''make sure confmon contains gateway'''
    systems = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').view

    def testHasGateway(self):
        '''make sure gateway is one of confmon's subsystems'''
        self.assertEqual(
            self.systems().find('"/dmd/Systems/Confmon/subsystems/Gateway"') != -1, 1)

if __name__=="__main__":
    unittest.main()
