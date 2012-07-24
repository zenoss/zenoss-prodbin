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
# the "Locations" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase

class TestLocations(SelTestBase):
    """Defines an object that runs tests under the Locations heading"""
    
    def testLocationOrganizer(self):
        """Run tests on the Locations page"""
        
        self.waitForElement("link=Locations")
        self.selenium.click("link=Locations")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog(new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)

        
if __name__ == "__main__":
    unittest.main()
