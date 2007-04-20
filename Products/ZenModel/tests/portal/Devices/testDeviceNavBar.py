###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class Edahl04TopTest(unittest.TestCase):
    '''test the nav bar for edahl04'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.Servers.Linux._getOb('edahl04.confmon.loc').top

    def testHasCrumbs(self):
        '''make sure we have the link to the directory below us'''
        self.assertEqual(
            self.dev().find('"/dmd/Devices/Servers/Linux"') != -1, 1)

    def testHasStatus(self):
        '''make sure we link to the status page'''
        self.assertEqual(
            self.dev().find('href="view"') != -1, 1)

    def testHasDetail(self):
        '''make sure we link to the detail screen'''
        self.assertEqual(
            self.dev().find('href="detail"') != -1, 1)

    def testHasEvents(self):
        '''make sure we link to the events screen'''
        self.assertEqual(
            self.dev().find('netcool/viewEvents') != -1, 1)

    def testHasPerformance(self):
        '''make sure we link to the performance screen'''
        self.assertEqual(
            self.dev().find('href="viewPerformance"') != -1, 1)

    def testHasChanges(self):
        '''make sure we link to the history screen'''
        self.assertEqual(
            self.dev().find('href="viewHistory"') != -1, 1)

class RouterTopTest(unittest.TestCase):
    '''test the nav bar for router'''
    dev = (makerequest.makerequest(Zope.app())).dmd.Devices.NetworkDevices.Router._getOb('router.confmon.loc').top

    def testHasCrumbs(self):
        '''make sure we have the link to the directory below us'''
        self.assertEqual(
            self.dev().find('"/dmd/Devices/NetworkDevices/Router"') != -1, 1)

    def testHasStatus(self):
        '''make sure we link to the status page'''
        self.assertEqual(
            self.dev().find('href="view"') != -1, 1)

    def testHasDetail(self):
        '''make sure we link to the detail screen'''
        self.assertEqual(
            self.dev().find('href="detail"') != -1, 1)

    def testHasEvents(self):
        '''make sure we link to the events screen'''
        self.assertEqual(
            self.dev().find('netcool/viewEvents') != -1, 1)

    def testHasPerformance(self):
        '''make sure we link to the performance screen'''
        self.assertEqual(
            self.dev().find('href="viewPerformance"') != -1, 1)

    def testHasChanges(self):
        '''make sure we link to the history screen'''
        self.assertEqual(
            self.dev().find('href="viewHistory"') != -1, 1)

if __name__=="__main__":
    unittest.main()
