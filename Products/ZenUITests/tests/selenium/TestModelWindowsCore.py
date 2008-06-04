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
# Contained below is the class that tests modeling the win2k-test2 device.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import *

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

