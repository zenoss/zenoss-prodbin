#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class LocationsListTest(unittest.TestCase):
    '''test the locations directory listing'''
    locs = (makerequest.makerequest(Zope.app())).dmd.Locations.index_html

    def testHasAnnapolis(self):
        '''make sure there is an Annapolis location'''
        self.assertEqual(
            self.locs().find('"/dmd/Locations/Annapolis"') != -1, 1)

class AnnapolisStatusTest(unittest.TestCase):
    '''test the status of the Annapolis location'''
    anp = (makerequest.makerequest(Zope.app())).dmd.Locations.Annapolis.view

    def testHasA1(self):
        '''make sure the A1 rack is at this location'''
        self.assertEqual(
            self.anp().find('"/dmd/Locations/Annapolis/racks/A1"') != -1, 1)

    def testHasB43(self):
        '''make sure the B43 rack is at this location'''
        self.assertEqual(
            self.anp().find('"/dmd/Locations/Annapolis/racks/B43"') != -1, 1)

    def testHasName(self):
        '''make sure it knows its name'''
        self.assertEqual(
            self.anp().find('Annapolis') != -1, 1)

class AnnapolisHistoryTest(unittest.TestCase):
    '''test the Annapolis history screen'''
    hist = (makerequest.makerequest(Zope.app())).dmd.Locations.Annapolis.viewHistory
    
    def testInitialLoad(self):
        '''make sure this was loaded by loader.py'''
        self.assertEqual(
            self.hist().find('Initial load') != -1, 1)

class AnnapolisTopTest(unittest.TestCase):
    '''test the nav bar of the Annapolis location'''
    top = (makerequest.makerequest(Zope.app())).dmd.Locations.Annapolis.top

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
