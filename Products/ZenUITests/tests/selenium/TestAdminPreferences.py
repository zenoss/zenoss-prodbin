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

from util.selTestUtils import *

from SelTestBase import SelTestBase

class TestAdminPreferences(SelTestBase):
    """Defines a class that runs tests under the Preference heading"""

    def _goToPreferences(self):

        self.waitForElement("link=Preferences")
        self.selenium.click("link=Preferences")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addAlertRule(self):

        self._goToPreferences()
        self.waitForElement("link=Alerting Rules")
        self.selenium.click("link=Alerting Rules")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=testingString"):
            self._deleteAlertRule()
        if self.selenium.is_element_present("link=testingString2"):
            self._deleteAlertRule2()
        self.addDialog("ActionRulelistaddActionRule",new_id=("text",
                    "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("ActionRulelistaddActionRule",new_id=("text",
                    "testingString2"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
       
    def _deleteAlertRule(self): 
        """Deletes the testing Alert Rule""" 
        self.waitForElement("link=Alerting Rules")
        self.selenium.click("link=Alerting Rules")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("ActionRulelistdeleteActionRules",
                "manage_deleteObjects:method", pathsList="ids:list",
                form_name="actionRules")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
           
    def _deleteAlertRule2(self): 
        """Deletes the second testing Alert Rule""" 
        self.deleteDialog("ActionRulelistdeleteActionRules",
                "manage_deleteObjects:method", pathsList="ids:list",
                form_name="actionRules", testData="testingString2")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testSavePreferences(self):
        """Run tests on the Edit Settings page"""
        self._goToPreferences() 
        self.selenium.click("name=manage_editUserSettings:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testSaveAdministeredObjects(self):
        """Run tests on the Administered Objects Settings page"""

        self._goToPreferences()
        self.waitForElement("link=Administered Objects")
        self.selenium.click("link=Administered Objects")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("name=manage_editAdministrativeRoles:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)    
        
    def testAddEventViews(self):
        """Run tests on the Event Views Table"""
        
        self._goToPreferences()
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

    def testAddAlertingRules(self):
        """Run tests on the Alerting Rules tab"""
        
        self._addAlertRule()
        #Selects All 
        self.waitForElement("id=selectall_0")
        self.selenium.click("id=selectall_0")
        do_command_byname(self.selenium, "assertChecked", "ids:list")
        self.selenium.click("id=selectnone_0")
        do_command_byname(self.selenium, "assertNotChecked", "ids:list")

        self.selenium.click("link=testingString")
        self.waitForElement("manage_editActionRule:method")
        self.selenium.click("manage_editActionRule:method")
       #self.selenium.wait_for_page_to_load(self.WAITTIME)

        #Tests the Message tab under an Alert Rule
        self.selenium.click("link=Message")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("manage_editActionRule:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

        #Tests the Schedule tab under an Alert Rule
        self.selenium.click("link=Schedule")
        self.addDialog("ActionRuleWindowlistaddActionRuleWindow",new_id=("text",
                    "testingStringSchedule"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=testingStringSchedule")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("manage_editActionRuleWindow:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=manage")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("ActionRuleWindowlistdeleteActionRuleWindows",
                "manage_deleteActionRuleWindow:method", pathsList="windowIds",
                form_name="actionRulesSchedule", testData="testingStringSchedule")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

        #Deletes the testing Alert Rule 
        self._deleteAlertRule()
        self._deleteAlertRule2()

if __name__ == "__main__":
    unittest.main()
