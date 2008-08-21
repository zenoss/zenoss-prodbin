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
# Thresholds for file systems and their event behavior.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import *

from SelTestBase import SelTestBase

class TestFileSystemThresholds(SelTestBase):
    """Defines an object that runs tests Filesystem Thresholds under a device
       OS tab"""

    
    def _changeCollectionTo5(self):
        sel = self.selenium
        sel.click("link=Collectors")
        sel.wait_for_page_to_load("30000")
        sel.click("//tbody[@id='Hubs']/tr[3]/td[1]/a")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Edit")
        sel.wait_for_page_to_load("30000")
        sel.type("perfsnmpCycleInterval:int", "5")
        sel.click("zmanage_editProperties:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Overview")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("5"))

    def _changeCollectionToDefault(self):
        sel = self.selenium
        sel.click("link=Collectors")
        sel.wait_for_page_to_load("30000")
        sel.click("//tbody[@id='Hubs']/tr[3]/td[1]/a")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Edit")
        sel.wait_for_page_to_load("30000")
        sel.type("perfsnmpCycleInterval:int", "300")
        sel.click("zmanage_editProperties:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Overview")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("300"))

    def testThresholdEventBehavior(self):

        sel = self.selenium
        self.addDeviceModel("build.zenoss.loc")
        self._changeCollectionTo5()
        sel.click("link=build.zenoss.loc")
        sel.wait_for_page_to_load("30000")
        sel.click("link=OS")
        sel.wait_for_page_to_load("30000")
        sel.click("link=/")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Template")
        sel.wait_for_page_to_load("30000")
        sel.click("makeLocalRRDTemplate:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=FileSystem")
        sel.wait_for_page_to_load("30000")
        self.waitForElement("link=Add Threshold...")
        sel.click("link=Add Threshold...")
        self.waitForElement("new_id")
        sel.type("new_id", "Really Low Threshold")
        sel.click("dialog_submit")
        sel.wait_for_page_to_load("30000")
        sel.add_selection("dsnames:list", "label=usedBlocks_usedBlocks")
        sel.type("maxval", "here.totalBlocks * .05")
        sel.click("zmanage_editProperties:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=FileSystem")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Free Space 90 Percent")
        sel.wait_for_page_to_load("30000")
        sel.select("enabled:boolean", "label=False")
        sel.click("zmanage_editProperties:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=FileSystem")
        sel.wait_for_page_to_load("30000")
        sel.click("link=build.zenoss.loc")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='contextmenu_btn']/a")
        sel.click("link=Model Device")
        sel.wait_for_page_to_load("30000")
        #sel.click("link=Event Console")
        #sel.wait_for_page_to_load("30000")
        #self.waitForElement("link=build.zenoss.loc")
        #self.failUnless(sel.is_text_present("threshold of Really Low Threshold exceeded: current value"))
        sel.click("link=build.zenoss.loc")
        sel.wait_for_page_to_load("30000")
        sel.click("link=OS")
        sel.wait_for_page_to_load("30000")
        sel.click("link=/")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Template")
        sel.wait_for_page_to_load("30000")
        sel.click("removeLocalRRDTemplate:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=FileSystem")
        sel.wait_for_page_to_load("30000")
        self.failIf(sel.is_element_present("link= Really Low Threshold"))
        self.waitForElement("query")
        self.selenium.type("query", "build")
        self.selenium.submit("searchform")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        #sel.click("//div[@id='tabsPane']/table/tbody/tr/td[6]/a")
        #sel.wait_for_page_to_load("30000")
        #self.waitForElement("link=build.zenoss.loc")
        #self.waitForElement("id=setSelectAll")
        #sel.click("id=setSelectAll")
        #self.waitForElement("link=Move to History...")
        #sel.click("link=Move to History...")
        #self.waitForElement("manage_deleteEvents:method")
        #sel.click("manage_deleteEvents:method")
        self._changeCollectionToDefault()
        self.deleteDevice("build.zenoss.loc")

if __name__ == "__main__":
   unittest.main()

