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

from util.selTestUtils import *

from SelTestBase import SelTestBase

class TestMonitors(SelTestBase):
    """Defines a class that runs tests under the Monitors heading"""

    def _addStatusMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=statusTestingString"):
            self._deleteStatusMonitor()
        self.addDialog("StatusMonitorlistaddSMonitor",new_id=("text",
                    "statusTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteStatusMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("StatusMonitorlistremoveSMonitors",
                "manage_removeMonitor:method", pathsList="ids:list", form_name="StatusMonitors", testData="statusTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addPerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=performanceTestingString"):
            self._deletePerformanceMonitor()
        self.addDialog("PerformanceMonitorlistaddPMonitor",new_id=("text",
                    "performanceTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deletePerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("PerformanceMonitorlistremovePMonitors",
                "manage_removeMonitor:method", pathsList="ids:list",
                form_name="Performance", testData="performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addPerformanceTemplate(self):
        self._addStatusMonitor()   
        self.waitForElement("id=StatusMonitorlistperformanceTemplates")
        self.selenium.click("id=StatusMonitorlistperformanceTemplates")
        self.addDialog("AllTemplatesaddTemplate","manage_addRRDTemplate:method", 
            new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
    def _deletePerformanceTemplate(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=StatusMonitorlistperformanceTemplates")
        self.selenium.click("id=StatusMonitorlistperformanceTemplates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("AllTemplatesdeleteTemplates",
                "manage_deleteRRDTemplates:method", pathsList="paths:list",
                form_name="performanceTemplates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteStatusMonitor()
        
    def testAddStatusMonitor(self):
        """Run tests on the Status Monitors table"""
        self._addStatusMonitor()   
        self._deleteStatusMonitor()
        
    def testAddPerformanceMonitor(self):
        """Run tests on the Performance Monitors table"""
        self._addPerformanceMonitor()
        self._deletePerformanceMonitor()       

    def _testEditPerformanceTemplateDescription(self):
        self._addPerformanceTemplate()
        self._deletePerformanceTemplate()

    def testEditStatusMonitorSettings(self):
        """Go into a Status Monitor, edit the time interval and verify the information is saved"""
        self._addStatusMonitor()   
        self.selenium.click("link=statusTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['zport/dmd/Monitors/StatusMonitors/statusTestingString/zmanage_editProperties'])
        self.selenium.click("link=Edit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("cycleInterval:int", "61") 
        self.selenium.type("timeOut:float", "1.6") 
        self.selenium.type("maxFailures:int", "1441") 
        self.selenium.type("chunk:int", "76") 
        self.selenium.type("tries:int", "3") 
        self.selenium.type("configCycleInterval:int", "21") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Overview")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['61'])
        self.selenium.do_command('assertTextPresent', ['1.6'])
        self.selenium.do_command('assertTextPresent', ['1441'])
        self.selenium.do_command('assertTextPresent', ['76'])
        self.selenium.do_command('assertTextPresent', ['3'])
        self.selenium.do_command('assertTextPresent', ['21'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['zport/dmd/Monitors/StatusMonitors/statusTestingString/zmanage_editProperties'])
        self._deleteStatusMonitor()

    def testEditPerformanceMonitorSettings(self):
        """Go into a Performance Monitor, edit the time interval and verify the information is saved"""
        self._addPerformanceMonitor()   
        self.selenium.click("link=performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Performance")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=graph_4_panr")
        self.waitForElement("id=linkcheck_label")
        self.selenium.do_command('assertTextPresent', ['Performance Graphs'])
        self.selenium.do_command('assertElementPresent', ['id=linkcheck_label'])
        self.selenium.do_command('assertElementPresent', ['id=graph_4_panr'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['/zport/dmd/Monitors/Performance/performanceTestingString/zmanage_editProperties'])
        self.selenium.click("link=Edit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("eventlogCycleInterval:int", "61") 
        self.selenium.type("perfsnmpCycleInterval:int", "301") 
        self.selenium.type("processCycleInterval:int", "181") 
        self.selenium.type("statusCycleInterval:int", "62") 
        self.selenium.type("winCycleInterval:int", "63") 
        self.selenium.type("winmodelerCycleInterval:int", "64") 
        self.selenium.type("configCycleInterval:int", "361") 
        self.selenium.type("renderurl", "/zport/RenderServerTest") 
        self.selenium.type("renderuser", "admin") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Overview")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['61'])
        self.selenium.do_command('assertTextPresent', ['301'])
        self.selenium.do_command('assertTextPresent', ['181'])
        self.selenium.do_command('assertTextPresent', ['62'])
        self.selenium.do_command('assertTextPresent', ['63'])
        self.selenium.do_command('assertTextPresent', ['64'])
        self.selenium.do_command('assertTextPresent', ['361'])
        self.selenium.do_command('assertTextPresent', ['/zport/RenderServerTest'])
        self.selenium.do_command('assertTextPresent', ['admin'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['/zport/dmd/Monitors/Performance/performanceTestingString/zmanage_editProperties'])
        self._deletePerformanceMonitor()



if __name__ == "__main__":
    unittest.main()
