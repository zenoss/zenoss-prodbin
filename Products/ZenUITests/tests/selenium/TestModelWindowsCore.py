#!/usr/bin/python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
# Contained below is the class that tests modeling the win2k-test2 device.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import TimeoutError, do_command_byname, getByValue

from SelTestBase import SelTestBase

dynamicdev = 'gate2.zenoss.loc'

class TestModelWindowsDevice(SelTestBase):
    """Defines an object that runs tests for modeling the win2k-test2 device"""

    def _setWindowszProperties(self):
        sel = self.selenium
        sel.click("link=Devices")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Server")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Windows")
        sel.wait_for_page_to_load("30000")
        sel.click("link=zProperties")
        sel.wait_for_page_to_load("30000")
        sel.type("zWinUser:string", "zenoss-test")
        sel.type("zWinPassword:string", "zenoss")
        sel.click("saveZenProperties:method")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Windows")
        sel.wait_for_page_to_load("30000")
   
    def testModelWin2kTest(self):
        """Tests Modeling win2k-test2"""
        sel = self.selenium
        self._setWindowszProperties()
        self.addDeviceModelWindows('win2k-test2.zenoss.loc')
        sel.click("link=OS")
        sel.wait_for_page_to_load("30000")
        sel.click("document.ipServiceListForm.onlyMonitored")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_element_present("link=epmap"))
        self.failUnless(sel.is_element_present("link=netbios-ns"))
        self.failUnless(sel.is_element_present("link=netbios-dgm"))
        self.failUnless(sel.is_element_present("link=netbios-ssn"))
        self.failUnless(sel.is_element_present("link=snmp"))
        self.failUnless(sel.is_element_present("link=microsoft-ds"))
        self.failUnless(sel.is_element_present("link=isakmp"))
        self.failUnless(sel.is_text_present("1 of 9"))
        self.deleteDevice('win2k-test.zenoss.loc')
   
        

if __name__ == "__main__":
        unittest.main()
