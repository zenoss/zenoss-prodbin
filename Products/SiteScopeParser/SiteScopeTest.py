###############################################################
#
# Copyright (c) 2002 Confmon Corporation. All Rights Reserved.
#
###############################################################

"""SiteScopeTest

A test framework for the SiteScopeParser class using unittest

$Id: SiteScopeTest.py,v 1.4 2002/05/02 21:02:36 alex Exp $"""

__version__ = "$Revision: 1.4 $"[10:-1]


import unittest
from SiteScopeParser import SiteScopeParser
from SiteScopeRow import SiteScopeRow

class testParser(unittest.TestCase):

    def setUp(self):
        file = open("html/DetailDNS.html","r")
        self.parser = SiteScopeParser()
        self.parser.feed(file.read())
        self.results = self.parser.getResults()

    def tearDown(self):
        self.parser = None
        self.results = None

    def testFirstHasKeys(self):
        self.assertEqual(len(self.results)<=0,0)

    def testFirstNameColumnValue(self):
        self.assertEqual(
            not self.results[0].Name(),0)

    def testFirstConditionData(self):
        self.assertEqual(
            not self.results[0].Condition(),0)

    def testSecondNameColumnValue(self):
        self.assertEqual(
            not self.results[1].Name(),0)

    def testSecondConditionData(self):
        self.assertEqual(
            not self.results[1].Condition(),0)

if __name__=="__main__":
    unittest.main()
