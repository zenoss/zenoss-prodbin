#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class GroupsListTest(unittest.TestCase):
    '''test the group directory listing'''
    group = (makerequest.makerequest(Zope.app())).dmd.Groups.index_html

    def testHasDevelopment(self):
        '''make sure there is a development group'''
        self.assertEqual(
            self.group().find('"/dmd/Groups/Development"') != -1, 1)

class DevelopmentStatusTest(unittest.TestCase):
    '''test the status of the development group'''
    group = (makerequest.makerequest(Zope.app())).dmd.Groups.Development.view

    def testHasEdahl04(self):
        '''make sure edahl04 is a member of this group'''
        self.assertEqual(
            self.group().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

    def testHasRouter(self):
        '''make sure router is a member of this group'''
        self.assertEqual(
            self.group().find('"/dmd/Devices/NetworkDevices/Router/router.confmon.loc"') != -1, 1)

    def testNoSubGroups(self):
        '''development shouldn't have subgroups'''
        self.assertEqual(
            self.group().find('No Sub-Groups') != -1, 1)

    def testHasName(self):
        '''make sure it knows its name'''
        self.assertEqual(
            self.group().find('Development') != -1, 1)

class DevelopmentHistoryTest(unittest.TestCase):
    '''test the development group history screen'''
    hist = (makerequest.makerequest(Zope.app())).dmd.Groups.Development.viewHistory
    
    def testInitialLoad(self):
        '''make sure this was loaded by loader.py'''
        self.assertEqual(
            self.hist().find('Initial load') != -1, 1)

class DevelopmentTopTest(unittest.TestCase):
    '''test the nav bar of the development group'''
    top = (makerequest.makerequest(Zope.app())).dmd.Groups.Development.top

    def testHasStatus(self):
        '''make sure the navbar has Status'''
        self.assertEqual(
            self.top().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure the navbar has changes'''
        self.assertEqual(
            self.top().find('href="viewHistory"') != -1, 1)

if __name__=="__main__":
    unittest.main()
