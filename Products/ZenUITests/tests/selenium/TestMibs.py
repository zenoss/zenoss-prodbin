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
# the "Mibs" Browse By subheading.
#
# Noel Brockett
#

import unittest

from SelTestBase import SelTestBase

class TestMibs(SelTestBase):
    """Defines a class that runs tests under the Mibs heading"""

    def _addMib(self):
        self.waitForElement("link=Mibs")
        self.selenium.click("link=Mibs")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=mibTestingString"):
            self._deleteMib()
        self.addDialog("MiblistaddMibModule",new_id=("text", "mibTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteMib(self):
        self.waitForElement("link=Mibs")
        self.selenium.click("link=Mibs")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("MiblistremoveMibModules",
                deleteMethod="removeMibModules:method", pathsList="ids:list",
                form_name="mibsForm", testData="mibTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testAddMibs(self):
        """Run tests on the Mibs page"""
        self._addMib()
        self._deleteMib()
        
    def testEditMibSettings(self):
        self._addMib()
        self.waitForElement("link=mibTestingString")
        self.selenium.click("link=mibTestingString")
        self.waitForElement("link=Edit")
        self.selenium.click("link=Edit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "mibTestingStringEdit")
        self.selenium.type("language", "Georgian")
        self.selenium.type("contact:text", "contactTestingString")
        self.selenium.type("description:text", "This is the best Mib ever!")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Overview")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['mibTestingStringEdit'])
        self.selenium.do_command('assertTextPresent', ['Georgian'])
        self.selenium.do_command('assertTextPresent', ['contactTestingString'])
        self.selenium.do_command('assertTextPresent', ['This is the best Mib ever!'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['/zport/dmd/Mibs/mibs/mibTestingString/zmanage_editProperties'])
        self.selenium.click("link=Edit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "mibTestingString")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Overview")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['mibTestingString'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent',
                ['/zport/dmd/Mibs/mibs/mibTestingStringEdit/zmanage_editProperties'])
        self._deleteMib()
    
    def testOIDMappings(self):
        self._addMib()
        self.waitForElement("link=mibTestingString")
        self.selenium.click("link=mibTestingString")
        self.addDialog("OIDMappingsaddOIDMapping",new_id=("text",
                    "oidTestingString"), oid=("text", "oidType"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=oidTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['oidTestingString'])
        self.selenium.do_command('assertTextPresent', ['oidType'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent',
                ['/zport/dmd/Mibs/mibs/mibTestingString/addMibNode'])
        self.waitForElement("link=Mibs")
        self.selenium.click("link=Mibs")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=mibTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("OIDMappingsdeleteOIDMapping",
                deleteMethod="deleteMibNodes:method", pathsList="ids:list",
                form_name="oidMappingsForm", testData="oidTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteMib()
    def testTraps(self):
        self._addMib()
        self.waitForElement("link=mibTestingString")
        self.selenium.click("link=mibTestingString")
        self.addDialog("TrapsaddTrap",new_id=("text",
                    "trapsTestingString"), oid=("text", "trapOidType"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=trapsTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['trapsTestingString'])
        self.selenium.do_command('assertTextPresent', ['trapOidType'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent',
                ['/zport/dmd/Mibs/mibs/mibTestingString/addMibNotification'])
        self.waitForElement("link=Mibs")
        self.selenium.click("link=Mibs")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=mibTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("TrapsdeleteTrap",
                deleteMethod="deleteMibNotifications:method", pathsList="ids:list",
                form_name="trapsForm", testData="trapsTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteMib()


if __name__ == "__main__":
    unittest.main()
