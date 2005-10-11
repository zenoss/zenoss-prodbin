#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class ConfmonTopTest(unittest.TestCase):
    '''test the nav bar for confmon'''
    system = (makerequest.makerequest(Zope.app())).dmd.Systems._getOb('Confmon').top

    def testHasCrumbs(self):
        '''make sure we have the link to the directory below us'''
        self.assertEqual(
            self.system().find('"/dmd/Systems"') != -1, 1)

    def testHasStatus(self):
        '''make sure we link to the status page'''
        self.assertEqual(
            self.system().find('href="view"') != -1, 1)

    def testHasDevices(self):
        '''make sure we link to the device screen'''
        self.assertEqual(
            self.system().find('href="device_view"') != -1, 1)

    def testHasEvents(self):
        '''make sure we link to the events screen'''
        self.assertEqual(
            self.system().find('netcool/viewEvents') != -1, 1)

    def testHasPerformance(self):
        '''make sure we link to the performance screen'''
        self.assertEqual(
            self.system().find('href="performance_view"') != -1, 1)

    def testHasChanges(self):
        '''make sure we link to the history screen'''
        self.assertEqual(
            self.system().find('href="viewHistory"') != -1, 1)
            
if __name__=="__main__":
    unittest.main()
