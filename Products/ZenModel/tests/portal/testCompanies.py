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

class ListCompanyTest(unittest.TestCase):
    '''test to see if we can navigate and investigate companies'''
    companies = (makerequest.makerequest(Zope.app())).dmd.Companies.index_html
    
    def testFindCisco(self):
        '''make sure cisco is in the companies directory'''
        self.assertEqual(
            self.companies().find('"/dmd/Companies/Cisco"') != -1, 1)

    def testFindCompaq(self):
        '''make sure compaq is in the companies directory'''
        self.assertEqual(
            self.companies().find('"/dmd/Companies/Compaq"') != -1, 1)

class CompaqStatusTest(unittest.TestCase):
    '''test the status page of the compaq company'''
    company = (makerequest.makerequest(Zope.app())).dmd.Companies.Compaq.view

    def testIsCompaq(self):
        '''make sure this is compaq'''
        self.assertEqual(
            self.company().find('Compaq') != -1, 1)

    def testHasDeskpro(self):
        '''make sure compaq has a deskpro product'''
        self.assertEqual(
            self.company().find('"/dmd/Products/Hardware/Deskpro"') != -1, 1)

class CompaqHistoryTest(unittest.TestCase):
    '''test the history page for compaq'''
    company = (makerequest.makerequest(Zope.app())).dmd.Companies.Compaq.viewHistory

    def testWasMadeByLoader(self):
        '''make sure the initial comment from loader.py is there'''
        self.assertEqual(
            self.company().find('Initial load') != -1, 1)

class CompaqTopTest(unittest.TestCase):
    '''test the nav bar for compaq'''
    company = (makerequest.makerequest(Zope.app())).dmd.Companies.Compaq.top

    def testHasStatus(self):
        '''make sure the navbar has status'''
        self.assertEqual(
            self.company().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure the navbar has changes'''
        self.assertEqual(
            self.company().find('href="viewHistory"') != -1, 1)

if __name__ == "__main__":
    unittest.main()
    
