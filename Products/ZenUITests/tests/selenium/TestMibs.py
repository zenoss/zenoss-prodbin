#!/usr/bin/python
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
# the "Mibs" Browse By subheading.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestMibs(SelTestBase):
    """Defines a class that runs tests under the Mibs heading"""

    def testAddMibs(self):
        """Run tests on the Mibs page"""
        
        self.waitForElement("link=Mibs")
        self.selenium.click("link=Mibs")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("MiblistaddMibModule",new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("MiblistremoveMibModules",
                deleteMethod="removeMibModules:method", pathsList="ids:list", form_name="mibsForm")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
if __name__ == "__main__":
    unittest.main()
