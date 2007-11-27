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
# the "Preference" option in the Settings Div.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestAdminPreferences(SelTestBase):
    """Defines a class that runs tests under the Preference heading"""

    def goToPreferences(self):

        self.waitForElement("link=Preferences")
        self.selenium.click("link=Preferences")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testSavePreferences(self):
        """Run tests on the Edit Settings page"""
        self.goToPreferences() 
        self.selenium.click("name=manage_editUserSettings:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
    def testSaveAdministeredObjects(self):
        """Run tests on the Administered Objects Settings page"""

        self.goToPreferences()
        self.waitForElement("link=Administered Objects")
        self.selenium.click("link=Administered Objects")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("name=manage_editAdministrativeRoles:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)    
        
    def testAddEventViews(self):
        """Run tests on the Event Views Table"""
        
        self.goToPreferences()
        self.waitForElement("link=Event Views")
        self.selenium.click("link=Event Views")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("EventViewlistaddEventView",new_id=("text",
                    "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("EventViewlistdeleteEventViews",
                "manage_deleteObjects:method", pathsList="ids:list",
                form_name="eventviewsForm")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
if __name__ == "__main__":
    unittest.main()
