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

    def testRunDNSForward(self):
        """Tests Run Command DNS forward for gate2.zenoss.loc"""
        sel = self.selenium
        self.addDevice('gate2.zenoss.loc')
        self.failUnless(sel.is_text_present("192.168.1.1"))
        sel.click("link=DNS forward")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/manageIp}"))
        self.failUnless(sel.is_text_present("==== gate2.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host 192.168.1.1"))
        self.failUnless(sel.is_text_present("1.1.168.192.in-addr.arpa domain name pointer gate2.zenoss.loc."))
        self.failUnless(sel.is_text_present("DONE"))
        self.deleteDevice('gate2.zenoss.loc') 
        
    def testRunDNSReverse(self):
        """Tests Run Command DNS Reverse for gate2.zenoss.loc"""
        sel = self.selenium
        self.addDevice('gate2.zenoss.loc')
        self.failUnless(sel.is_text_present("192.168.1.1"))
        sel.click("link=DNS reverse")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/id}"))
        self.failUnless(sel.is_text_present("==== gate2.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host gate2.zenoss.loc"))
        self.failUnless(sel.is_text_present("gate2.zenoss.loc has address 192.168.1.1"))
        self.failUnless(sel.is_text_present("DONE"))
        self.deleteDevice('gate2.zenoss.loc') 

    def testRunDNSForwardClass(self):
        """Tests Run Command DNS forward for the class /Server/Linux"""
        sel = self.selenium
        self.addDevice('build.zenoss.loc')
        self.addDevice('gate2.zenoss.loc')
        sel.click("link=Linux")
        sel.wait_for_page_to_load("30000")
        sel.click("link=DNS forward")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/manageIp}"))
        self.failUnless(sel.is_text_present("==== gate2.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host 192.168.1.1"))
        self.failUnless(sel.is_text_present("1.1.168.192.in-addr.arpa domain name pointer gate2.zenoss.loc."))
        self.failUnless(sel.is_text_present("==== build.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host 10.175.211.17"))
        self.failUnless(sel.is_text_present("17.211.175.10.in-addr.arpa domain name pointer build.zenoss.loc."))
        self.failUnless(sel.is_text_present("DONE"))
        self.failUnless(sel.is_text_present("2 targets"))
        self.deleteDevice('build.zenoss.loc') 
        self.deleteDevice('gate2.zenoss.loc') 

    def testRunDNSReverseClass(self):
        """Tests Run Command DNS reverse for the class /Server/Linux"""
        sel = self.selenium
        self.addDevice('build.zenoss.loc')
        self.addDevice('gate2.zenoss.loc')
        sel.click("link=Linux")
        sel.wait_for_page_to_load("30000")
        sel.click("link=DNS reverse")
        sel.wait_for_page_to_load("30000")
        self.failUnless(sel.is_text_present("Command Output"))
        self.failUnless(sel.is_text_present("Command: host ${device/id}"))
        self.failUnless(sel.is_text_present("==== gate2.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host gate2.zenoss.loc"))
        self.failUnless(sel.is_text_present("gate2.zenoss.loc has address 192.168.1.1"))
        self.failUnless(sel.is_text_present("==== build.zenoss.loc ===="))
        self.failUnless(sel.is_text_present("host build.zenoss.loc"))
        self.failUnless(sel.is_text_present("build.zenoss.loc has address 10.175.211.17"))
        self.failUnless(sel.is_text_present("DONE"))
        self.failUnless(sel.is_text_present("2 targets"))
        self.deleteDevice('build.zenoss.loc') 
        self.deleteDevice('gate2.zenoss.loc') 

if __name__ == "__main__":
        unittest.main()

