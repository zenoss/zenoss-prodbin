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

class TestEvents(SelTestBase):
    """
    Defines an object that runs tests under the Events heading.
    """

    def testEventClass(self):
        """Run tests on the Events page."""

        self.waitForElement("link=Events")
        self.selenium.click("link=Events")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog(new_id=("text", "testingString"))
        self.deleteDialog(form_name="subclasses")
        
    def moveEventClassMappings(self, pathsList="ids:list", form_name="mappings", moveTo="/Unknown", stringval="testingString"):
        """Test moving an EventClassMapping to /Unknown."""
        
        self.waitForElement(getByValue(pathsList, stringVal, form_name))
        self.selenium.click(getByValue(pathsList, stringVal, form_name))
        self.waitForElement("EventmappinglistmoveInstances")
        self.selenium.click("EventMappinglistmoveInstances")
        self.waitForElement("moveInstances:method")
        self.selenium.select("moveTarget", moveTo)
        self.selenium.click("moveInstances:method")
        
if __name__ == "__main__":
    unittest.main()
