##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below is the class that tests Search functionality.
#
# Nate Avers
#

import unittest

from SelTestBase import SelTestBase,TARGET

class TestSearch(SelTestBase):
    """Defines a class that tests search functionality."""
    
    def setUp(self):
        """Adds functionality to SelTestBase.setUp"""
        SelTestBase.setUp(self)
        self.addDevice()
        
    def tearDown(self):
        """Adds functionality to SelTestBase.tearDown"""
        self.deleteDevice()
        SelTestBase.tearDown(self)
        
    def testSearch(self):
        """Test device search"""
        self.waitForElement("query")
        self.selenium.type("query", TARGET)
        self.selenium.submit("searchform")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.assert_(self.selenium.is_element_present("link=%s" %TARGET))
        self.selenium.click("link=%s" %TARGET)
        self.selenium.wait_for_page_to_load(self.WAITTIME)

if __name__ == "__main__":
    unittest.main()
