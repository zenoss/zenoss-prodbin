#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
import Zope
from Testing import makerequest

class DmdIndexTest(unittest.TestCase):
    '''check to see if anything is wrong with the dmd main frameset'''
    request = (makerequest.makerequest(Zope.app())).dmd.index_html()

    def testHasTitle(self):
        '''check to see that the title is there'''
        self.assertEqual(
            self.request.find('Device Management Database') != -1, 1)

    def testLeftFrameName(self):
        '''check to make sure the name of the left frame is right'''
        self.assertEqual(
            self.request.find('name="leftFrame"') != -1, 1)

    def testLeftFrameSrc(self):
        '''check to make sure the src of the left frame is right'''
        self.assertEqual(
            self.request.find('src="left"') != -1, 1)

    def testRightFrameName(self):
        '''check to make sure the name of the right frame is right'''
        self.assertEqual(
            self.request.find('name="rightFrame"') != -1, 1)

    def testRightFrameSrc(self):
        '''check to make sure the src of the right frame is right'''
        self.assertEqual(
            self.request.find('src="home_html"') != -1, 1)

if __name__=="__main__":
    unittest.main()
