#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class Edahl04ChangesTest(unittest.TestCase):
    '''check edahl04 for the initial load entry'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').viewHistory

    def testFindInitialLoad(self):
        '''look for the initial load'''
        self.assertEqual(
            self.dev().find('Initial load') != -1, 1)

class RouterChangeTest(unittest.TestCase):
    '''check router for the initial load entry'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').viewHistory

    def testFindInitialLoad(self):
        '''look for the initial load'''
        self.assertEqual(
            self.dev().find('Initial load') != -1, 1)

if __name__=="__main__":
    unittest.main()
