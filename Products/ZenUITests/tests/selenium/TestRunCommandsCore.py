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
# Contained below is the class that tests the Run Commands.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import *

from SelTestBase import SelTestBase

dynamicdev = 'gate2.zenoss.loc'

class TestRunCommands(SelTestBase):
    """Defines an object that runs tests for the for run commands under a
       device"""

    def _addSubClass(self):
        self.waitForElement("link=Devices")
        self.selenium.click("link=Devices")
        self.waitForElement("link=Server")
        self.selenium.click("link=Server")
        self.selenium.wait_for_page_to_load("30000")
        if self.selenium.is_element_present("link=testingString"):
            self.deleteDialog()
        self.addDialog(addMethod="manage_addOrganizer:method",new_id=("text",
                    "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteSubClass(self):
        self.waitForElement("link=Devices")
        self.selenium.click("link=Devices")
        self.waitForElement("link=Server")
        self.selenium.click("link=Server")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testRunDNSForward(self):
        """Tests Run Command DNS forward for tilde"""
        sel = self.selenium
        self.addDevice('tilde')
        self.failUnless(sel.is_text_present("10.175.211.10"))
        sel.click("link=DNS forward")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/manageIp}"))
        self.failUnless(sel.is_text_present("==== tilde ===="))
        self.failUnless(sel.is_text_present("host 10.175.211.10"))
        self.failUnless(sel.is_text_present("10.211.175.10.in-addr.arpa domain name pointer tilde.zenoss.loc."))
        self.failUnless(sel.is_text_present("DONE"))
        self.deleteDevice('tilde') 
        
    def testRunDNSReverse(self):
        """Tests Run Command DNS Reverse for tilde"""
        sel = self.selenium
        self.addDevice('tilde')
        self.failUnless(sel.is_text_present("10.175.211.10"))
        sel.click("link=DNS reverse")
        sel.wait_for_page_to_load("30000")
        for i in range(60):
            try:
                if sel.is_text_present("DONE"): break
            except: pass
            time.sleep(1)
        else: self.fail("time out")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/id}"))
        self.failUnless(sel.is_text_present("==== tilde ===="))
        self.failUnless(sel.is_text_present("host tilde"))
        self.failUnless(sel.is_text_present("tilde.zenoss.loc has address 10.175.211.10"))
        self.failUnless(sel.is_text_present("DONE"))
        self.deleteDevice('tilde') 

    def testRunDNSForwardClass(self):
        """Tests Run Command DNS forward for the class /Server/testingString"""
        sel = self.selenium
        self._addSubClass()
        self.addDevice('build.zenoss.loc', classPath="/Server/testingString")
        self.addDevice('tilde', classPath="/Server/testingString")
        sel.click("link=testingString")
        sel.wait_for_page_to_load("30000")
        sel.click("link=DNS forward")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/manageIp}"))
        self.failUnless(sel.is_text_present("==== tilde ===="))
        self.failUnless(sel.is_text_present("host 10.175.211.10"))
        self.failUnless(sel.is_text_present("10.211.175.10.in-addr.arpa domain name pointer tilde.zenoss.loc"))
        self.failUnless(sel.is_text_present("==== build.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host 10.175.211.17"))
        self.failUnless(sel.is_text_present("17.211.175.10.in-addr.arpa domain name pointer build.zenoss.loc."))
        self.failUnless(sel.is_text_present("DONE"))
        self.failUnless(sel.is_text_present("2 targets"))
        self.deleteDevice('build.zenoss.loc') 
        self.deleteDevice('tilde') 
        self._deleteSubClass()

    def testRunDNSReverseClass(self):
        """Tests Run Command DNS reverse for the class /Server/testingString"""
        sel = self.selenium
        self._addSubClass()
        self.addDevice('build.zenoss.loc', classPath="/Server/testingString")
        self.addDevice('tilde', classPath="/Server/testingString")
        sel.click("link=testingString")
        sel.wait_for_page_to_load("30000")
        sel.click("link=DNS reverse")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/id}"))
        self.failUnless(sel.is_text_present("==== tilde ===="))
        self.failUnless(sel.is_text_present("host tilde"))
        self.failUnless(sel.is_text_present("tilde.zenoss.loc has address 10.175.211.10"))
        self.failUnless(sel.is_text_present("==== build.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host build.zenoss.loc"))
        self.failUnless(sel.is_text_present("build.zenoss.loc has address 10.175.211.17"))
        self.failUnless(sel.is_text_present("DONE"))
        self.failUnless(sel.is_text_present("2 targets"))
        self.deleteDevice('build.zenoss.loc') 
        self.deleteDevice('tilde') 
        self._deleteSubClass()

if __name__ == "__main__":
        unittest.main()

