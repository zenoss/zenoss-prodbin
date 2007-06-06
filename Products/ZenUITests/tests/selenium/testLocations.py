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

#
# Contained below is the class that tests elements located under
# the "Locations" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from selTestBase import selTestBase

class LocationsTest(selTestBase):
    """Defines an object that runs tests under the Locations heading."""
    
    def testLocationOrganizer(self):
        """Run tests on the Locations page.
        """
        self.waitForElement("link=Locations")
        self.selenium.click("link=Locations")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load("30000")

        
if __name__ == "__main__":
    unittest.main()