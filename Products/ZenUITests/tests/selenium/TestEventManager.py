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
# the "Event Manager" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from selTestBase import selTestBase

class TestEventManager(SelTestBase):
    """Defines a class that runs tests under the Event Manager heading."""

    def testRefreshEventSchema(self):
        """
        Run tests on the Groups page.
        """
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Refresh Event Schema...")
        self.selenium.click("link=Refresh Event Schema...")    
        self.waitForElement("manage_refreshConversions:method")
        self.selenium.click("manage_refreshConversions:method")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.click("manage_editEventManager:method")
        
    def testClearEventCache(self):
        """
        Test clearing all heartbeats.
        """
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Clear Event Cache...")
        self.selenium.click("link=Clear Event Cache...")
        self.waitForElement("manage_clearCache:method")
        self.selenium.click("manage_clearCache:method")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.click("manage_editEventManager:method")
        
    def testClearAllHeartbeats(self):
        """
        Test clearing all heartbeats.
        """
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Clear All Heartbeats...")
        self.selenium.click("link=Clear All Heartbeats...")
        self.waitForElement("manage_clearHeartbeats:method")
        self.selenium.click("manage_clearHeartbeats:method")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.click("manage_editEventManager:method")
        
    def testEditEventManager(self):
        """
        Test clearing all heartbeats.
        """
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        #Edit the Event Manager
        self.waitForElement("history_clearthresh:int")
        self.selenium.type("timeout:int", "19")
        self.selenium.type("clearthresh:int", "19")
        self.selenium.type("history_timeout:int", "299")
        self.selenium.type("history_clearthresh:int", "19")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.click("manage_editEventManager:method")
        self.selenium.wait_for_page_to_load("30000")
        #Change back to initial values
        self.waitForElement("history_clearthresh:int")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.type("timeout:int", "20")
        self.selenium.type("clearthresh:int", "20")
        self.selenium.type("history_timeout:int", "300")
        self.selenium.type("history_clearthresh:int", "20")
        self.waitForElement("manage_editEventManager:method")
        self.selenium.click("manage_editEventManager:method")    
        
    def testEditFields(self):
        """
        Test editing the fields tab.
        """    
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Fields")
        self.selenium.click("link=Fields")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("zmanage_editProperties:method")
        self.selenium.click("zmanage_editProperties:method")
    
    def testCommands(self):
        """
        Test adding, editing and deleting commands
        """
        self.waitForElement("link=Event Manager")
        self.selenium.click("link=Event Manager")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Commands")
        self.selenium.click("link=Commands")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("manage_addCommand:method")
        self.selenium.type("id", "testingString")
        self.selenium.click("manage_addCommand:method")
        self.getByValue (listName, value, formName="clauseForm")
        self.waitForElement("manage_deleteCommands:method")
        self.selenium.click("manage_deleteCommands:method")
    
    
    
if __name__ == "__main__":
    unittest.main()