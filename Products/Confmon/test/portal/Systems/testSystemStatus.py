#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class ConfmonStatusTest(unittest.TestCase):
    '''check the status screen for the confmon system'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').view

    def testIsConfmon(self):
        '''look for the word Confmon'''
        self.assertEqual(
            self.system().find('Confmon') != -1, 1)

    def testPingStatus(self):
        '''look for the ping status'''
        self.assertEqual(
            self.system().find('100%') != -1, 1)

    def testProdState(self):
        '''make sure the prod state is pre-production'''
        self.assertEqual(
            self.system().find('Pre-Production') != -1, 1)

    def testNoServiceAreas(self):
        '''make sure there arent any service areas'''
        self.assertEqual(
            self.system().find('No Service Areas') != -1, 1)

class GatewayStatusTest(unittest.TestCase):
    '''test the gateway subsystems's status screen'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems.Confmon.subsystems._getOb('Gateway').view

    def testKnowsParent(self):
        '''make sure gateway knows it's in confmon'''
        self.assertEqual(
            self.system().find("'/dmd/Systems/Confmon'") != -1, 1)

    def testNoServiceAreas(self):
        '''make sure it's not in any service areas'''
        self.assertEqual(
            self.system().find('No Service Areas') != -1, 1)

    def testNoSubSystems(self):
        '''make sure it doesn't have any subsystems'''
        self.assertEqual(
            self.system().find('No Subsystems') != -1, 1)

    def testPingStatus(self):
        '''make sure the ping status is 100%'''
        self.assertEqual(
            self.system().find('100%') != -1, 1)

    def testProdState(self):
        '''make sure the prod state is pre-production'''
        self.assertEqual(
            self.system().find('Pre-Production') != -1, 1)
    
if __name__=="__main__":
    unittest.main()
