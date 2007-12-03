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
# Contained below is the class that tests various actions related to
# modification of a specific device instance.
#
# Adam Modlin and Nate Avers
#

import unittest

from util.selTestUtils import *

from SelTestBase import SelTestBase

class TestDeviceListBase(SelTestBase):
    """Base class for performing tests on specific device instances"""

    devicenames = []

    def setUp(self):
        """Customized setUp for device instance tests"""

        SelTestBase.setUp(self)
        self.addDevice('localhost')
        self.addDevice('zenosst.zenoss.loc')


    def tearDown(self):
        """Customized tearDown for device instance tests"""

        for devicename in self.devicenames:
            self.goToDevice(devicename)
        self.deleteDevice()

        SelTestBase.tearDown(self)



class TestDeviceList(TestDeviceListBase):
    """Test the device list"""

    def _goToDeviceList(self):
        self.waitForElement("link=Device List")
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _goToGroupsAddOrganizer(self):
        self.waitForElement("link=Groups")
        self.selenium.click("link=Groups")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=testingString"):
                self.deleteDialog()
        self.addDialog(new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _goToGroupsDeleteOrganizer(self):
        self.waitForElement("link=Groups")
        self.selenium.click("link=Groups")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load(self.WAITTIME)


    def testSelectAll(self):
        """Test Selecting all devices"""
        self._goToDeviceList() 
        self.waitForElement("id=setSelectAll")
        self.selenium.click("id=setSelectAll")
        do_command_byname(self.selenium, "assertChecked", "evids:list")
        self.selenium.click("id=setSelectNone")
        do_command_byname(self.selenium, "assertNotChecked", "evids:list")

    def _testSetPriority(self):
        """Test Setting Priority to the Highest"""
        curtarget = "zenosst.zenoss.loc"
        self._goToDeviceList() 
        self.selenium.click("name=evids:list " + curtarget)
        self.selenium.click("link=Set Priority...")
        self.waitForElement("setProductionState:method")
        self.selenium.select('priority', 'value=5')
        self.selenium.click("setProductionState:method")
        self.selenium.do_command("waitForText",
                ['id=messageSlot', 'Priority set to Highest'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertTextPresent', ['Highest',])

    def _testSetProductionState(self):
        """Test Setting Production state to the Test"""
        curtarget = "zenosst.zenoss.loc"
        self._goToDeviceList() 
        self.selenium.click("name=evids:list " + curtarget)
        self.selenium.click("link=Set Production State...")
        self.waitForElement("setProductionState:method")
        self.selenium.select('state', 'value=400')
        self.selenium.click("setProductionState:method")
        self.selenium.do_command("waitForText",
                ['id=messageSpan'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertTextPresent', ['Test'])

    def _testMoveClass(self):
        """Test Moving Class to /Server/Windows"""
        curtarget = "zenosst.zenoss.loc"
        self._goToDeviceList() 
        self.selenium.click("name=evids:list " + curtarget)
        self.selenium.click("link=Move to Class...")
        self.waitForElement("moveDevicesToClass:method")
        self.selenium.select('moveTarget', 'label=/Server/Windows')
        self.selenium.click("moveDevicesToClass:method")
        self.selenium.do_command("waitForText",
                ['id=messageSlot', 'Devices moved to /Server/Windows'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertTextPresent', ['/Server/Windows'])

    def _testSetGroups(self):
        """Test Setting the group to testingString"""
        curtarget = "zenosst.zenoss.loc"
        self._goToGroupsAddOrganizer()
        self._goToDeviceList() 
        self.selenium.click("name=evids:list " + curtarget)
        self.selenium.click("link=Set Groups...")
        self.waitForElement("setGroups:method")
        self.selenium.select('groupPaths', 'value=/testingString')
        self.selenium.click("setGroups:method")
        self.selenium.do_command("waitForElementPresent",
                ['id=messageSpan'])
        self.selenium.do_command('assertElementPresent', ['link=/testingString'])
        self._goToGroupsDeleteOrganizer()

if __name__ == "__main__":
   unittest.main()

