#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.2 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class ProductListTest(unittest.TestCase):
    '''test to see if we can navigate and investigate products'''
    products = (makerequest.makerequest(Zope.app())).dmd.Products.index_html
    
    def testFindHardware(self):
        '''make sure hardware is in the products directory'''
        self.assertEqual(
            self.products().find('"/dmd/Products/Hardware"') != -1, 1)

    def testFindSoftware(self):
        '''make sure software is in the products directory'''
        self.assertEqual(
            self.products().find('"/dmd/Products/Software"') != -1, 1)

class HardwareListTest(unittest.TestCase):
    '''test to see if we can navigate and investigate hardware products'''
    products = (makerequest.makerequest(Zope.app())).dmd.Products.Hardware.index_html

    def testFindDeskpro(self):
        '''make sure the deskpro hardware is here'''
        self.assertEqual(
            self.products().find('"/dmd/Products/Hardware/Deskpro"') != -1, 1)

    def testFind1602(self):
        '''make sure the 1602 platform is here'''
        self.assertEqual(
            self.products().find('"/dmd/Products/Hardware/1602"') != -1, 1)

class DeskproStatusTest(unittest.TestCase):
    '''test the status page of the deskpro product'''
    product = (makerequest.makerequest(Zope.app())).dmd.Products.Hardware.Deskpro.view

    def testIsDeskpro(self):
        '''make sure this is deskpro'''
        self.assertEqual(
            self.product().find('Deskpro') != -1, 1)

    def testHasEdahl04(self):
        '''make sure deskpro has edahl04'''
        self.assertEqual(
            self.product().find('"/dmd/Devices/Servers/Linux/edahl04.confmon.loc"') != -1, 1)

class DeskproHistoryTest(unittest.TestCase):
    '''test the history page for compaq'''
    product = (makerequest.makerequest(Zope.app())).dmd.Products.Hardware.Deskpro.viewHistory

    def testWasMadeByLoader(self):
        '''make sure the initial comment from loader.py is there'''
        self.assertEqual(
            self.product().find('Initial load') != -1, 1)

class DeskproTopTest(unittest.TestCase):
    '''test the nav bar for deskpro'''
    product = (makerequest.makerequest(Zope.app())).dmd.Products.Hardware.Deskpro.top

    def testHasStatus(self):
        '''make sure the navbar has status'''
        self.assertEqual(
            self.product().find('href="view"') != -1, 1)

    def testHasChanges(self):
        '''make sure the navbar has changes'''
        self.assertEqual(
            self.product().find('href="viewHistory"') != -1, 1)

if __name__ == "__main__":
    unittest.main()
