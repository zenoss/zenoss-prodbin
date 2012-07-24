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
# the "Settings" Browse By subheading.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestSettings(SelTestBase):
    """Defines a class that runs tests under the Settings heading"""

    def testSaveSettings(self):
        """Run tests on the Settings page"""
        
        self.waitForElement("link=Settings")
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()
