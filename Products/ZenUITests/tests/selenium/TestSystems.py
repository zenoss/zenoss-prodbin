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
# the "Systems" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase

class TestSystems(SelTestBase):
    """Defines a class that runs tests under the Systems heading"""

    def testSystemOrganizer(self):
        """Run tests on the Systems page"""
        
        self.waitForElement("link=Systems")
        self.selenium.click("link=Systems")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog(new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()
