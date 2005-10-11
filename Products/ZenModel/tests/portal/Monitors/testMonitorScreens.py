#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class CricketStatusTest(unittest.TestCase):
    '''test the status page of the cricket monitor'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.Cricket._getOb('edahl04.confmon.loc').view

    def testIsCricket(self):
        '''make sure this is cricket'''
        self.assertEqual(
            self.monitor().find('Cricket Configuration') != -1, 1)

    def testHasEdahl(self):
        '''make sure cricket has edahl04'''
        self.assertEqual(
            self.monitor().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testHasRouter(self):
        '''make sure cricket has router'''
        self.assertEqual(
            self.monitor().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

class CricketHistoryTest(unittest.TestCase):
    '''test the history page for cricket'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.Cricket._getOb('edahl04.confmon.loc').viewHistory

    def testWasMadeByLoader(self):
        '''make sure the initial comment from loader.py is there'''
        self.assertEqual(
            self.monitor().find('Initial load') != -1, 1)

class CricketTopTest(unittest.TestCase):
    '''test the nav bar for cricket'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.Cricket._getOb('edahl04.confmon.loc').top

    def testHasStatus(self):
        '''make sure the navbar has status'''
        self.assertEqual(
            self.monitor().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure the navbar has changes'''
        self.assertEqual(
            self.monitor().find('href="viewHistory"') != -1, 1)

class PingMonitorStatusTest(unittest.TestCase):
    '''check the status page of a pingmonitor'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.PingMonitors._getOb('Default').view

    def testIsDefault(self):
        '''make sure it's who we think'''
        self.assertEqual(
            self.monitor().find('Default') != -1, 1)

    def testChunkSize(self):
        '''find the chunk size'''
        self.assertEqual(
            self.monitor().find('50') != -1, 1)

    def testTimeout(self):
        '''find the timeout'''
        self.assertEqual(
            self.monitor().find('1.0') != -1, 1)

    def testHasEdahl(self):
        '''make sure edahl04 is monitored'''
        self.assertEqual(
            self.monitor().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testHasRouter(self):
        '''make sure router is monitored'''
        self.assertEqual(
            self.monitor().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

class PingMonitorHistoryTest(unittest.TestCase):
    '''make sure this was made by loader.py'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.PingMonitors._getOb('Default').viewHistory

    def testHasInitialLoad(self):
        '''look for initial load'''
        self.assertEqual(
            self.monitor().find('Initial load') != -1, 1)

class PingMonitorTopTest(unittest.TestCase):
    '''make sure the navbar is right'''
    monitor = (makerequest.makerequest(Zope.app())).dmd.Monitors.PingMonitors._getOb('Default').top

    def testHasStatus(self):
        '''make sure it has status'''
        self.assertEqual(
            self.monitor().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure it has changes'''
        self.assertEqual(
            self.monitor().find('href="viewHistory"') != -1, 1)

if __name__ == "__main__":
    unittest.main()
