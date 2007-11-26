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
# the "Networks" Browse By subheading.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestMonitors(SelTestBase):
    """Defines a class that runs tests under the Monitors heading"""

    def testAddStatusMonitor(self):
        """Run tests on the Status Monitors table"""
        
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("StatusMonitorlistaddSMonitor",new_id=("text",
                    "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("StatusMonitorlistremoveSMonitors",
                "manage_removeMonitor:method", pathsList="ids:list", form_name="StatusMonitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def testAddPerformanceMonitor(self):
        """Run tests on the Perfirmance Monitors table"""
        
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.addDialog("PerformanceMonitorlistaddPMonitor",new_id=("text",
                    "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("PerformanceMonitorlistremovePMonitors",
                "manage_removeMonitor:method", pathsList="ids:list",
                form_name="Performance")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
if __name__ == "__main__":
    unittest.main()
