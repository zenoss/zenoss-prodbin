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
# the "Events" Browse By subheading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase
from util.selTestUtils import getByValue

class TestEvents(SelTestBase):
    """Defines an object that runs tests under the Events heading"""

    def testEventClass(self):
        """Test adding and deleting event classes"""

        self.waitForElement("link=Events")
        self.selenium.click("link=Events")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog(new_id=("text", "testParent"))
        self.assert_(self.selenium.is_element_present("link=testParent"))
        self.selenium.click("link=testParent")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog(new_id=("text", "testChild1"))
        self.addDialog(new_id=("text", "testChild2"))
        self.addDialog(new_id=("text", "testChild3"))
        self.addDialog(new_id=("text", "testChild4"))
        self.addDialog(new_id=("text", "testChild5"))
        self.selenium.click(getByValue("organizerPaths:list", "testChild2", "subclasses"))
        self.selenium.click(getByValue("organizerPaths:list", "testChild4", "subclasses"))
        self.selenium.click("OrganizerlistremoveOrganizers")
        self.waitForElement("manage_deleteOrganizers:method")
        self.selenium.click("manage_deleteOrganizers:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.assert_(not self.selenium.is_element_present("testChild2"))
        self.assert_(not self.selenium.is_element_present("testChild4"))
        self.selenium.click("link=Events")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog(testData="testParent", form_name="subclasses")
        self.assert_(not self.selenium.is_element_present("testParent"))
    
    def testAddEvent(self):
        """Test adding an event and moving it to history"""
            
        
    def moveEventClassMappings(self, pathsList="ids:list", form_name="mappings", moveTo="/Unknown", stringVal="testingString"):
        """Test moving an EventClassMapping to /Unknown"""
        
        self.waitForElement(getByValue(pathsList, stringVal, form_name))
        self.selenium.click(getByValue(pathsList, stringVal, form_name))
        self.waitForElement("EventmappinglistmoveInstances")
        self.selenium.click("EventMappinglistmoveInstances")
        self.waitForElement("moveInstances:method")
        self.selenium.select("moveTarget", moveTo)
        self.selenium.click("moveInstances:method")
        
if __name__ == "__main__":
    unittest.main()
