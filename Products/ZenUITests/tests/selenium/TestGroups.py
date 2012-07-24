#!/usr/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below is the class that tests elements located under
# the "Groups" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase

class TestGroups(SelTestBase):
    """Defines a class that runs tests under the Groups heading"""

    def testGroupOrganizer(self):
        """Run tests on the Groups page"""
        
        self.waitForElement("link=Groups")
        self.selenium.click("link=Groups")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=testingString"):
                self.deleteDialog()
        self.addDialog(new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()
