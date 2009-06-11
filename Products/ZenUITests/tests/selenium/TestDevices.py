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
# the "Devices" class heading.
#
# Adam Modlin and Nate Avers
#

import unittest

from SelTestBase import SelTestBase

class TestDevices(SelTestBase):
    """Defines an object that runs tests against a Device Class"""
    
    def testDeviceClass(self):
        """Run tests on the Devices page"""
        self.waitForElement("link=Devices")
        self.selenium.click("link=Devices")
        self.waitForElement("link=Templates")
        self.selenium.click("link=Templates")
        self.addDialog(addType="TemplatesaddTemplate", new_id=("text", "testingString"))
        self.deleteDialog(deleteType="TemplatesdeleteTemplates", deleteMethod="manage_deleteRRDTemplates:method",
                            pathsList="ids:list", form_name="templates")
        
    def testEditZProperty(self):
        """Test changing zCommandProtocol in /Server from ssh to telnet and back"""
        
        # Navigate to zProperites page of /Server
        self.selenium.click("link=Devices")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Server")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=zProperties")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
        # Enter new value and make sure everything's ok
        self.selenium.select("zCommandProtocol", "telnet")
        self.selenium.click("saveZenProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.assert_(self.selenium.get_value("zCommandProtocol") == "telnet")
        # Hardcoding table row is gross, but don't have the javascript to find it by value
#        self.assert_(self.selenium.get_table("zPropertiesConfiguration.13.3") == "/Server")
        
        # Change it back and make sure everything's the way it was
        self.selenium.select("propname", "zCommandProtocol")
        self.selenium.click("deleteZenProperty:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.assert_(self.selenium.get_value("zCommandProtocol") == "ssh")
        # Ditto gross
#        self.assert_(self.selenium.get_table("zPropertiesConfiguration.13.3") == "/")
        
if __name__ == "__main__":
    unittest.main()
