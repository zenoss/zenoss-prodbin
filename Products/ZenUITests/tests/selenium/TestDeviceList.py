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

secondarydev = 'zenosst'

class TestDeviceListBase(SelTestBase):
    """Base class for performing tests on specific device instances"""

    devicenames = []

    def setUp(self):
        """Customized setUp for device instance tests"""

        SelTestBase.setUp(self)
        self.addDevice('localhost')
        self.addDevice(secondarydev)


    def tearDown(self):
        """Customized tearDown for device instance tests"""

        for devicename in self.devicenames:
            self.deleteDevice(devicename)

        SelTestBase.tearDown(self)



class TestDeviceList(TestDeviceListBase):
    """Test the device list"""

    def _clickDeviceInList(self, targetname=secondarydev):
        self.waitForElement("name=evids:list " + targetname)
        self.selenium.click("name=evids:list " + targetname)

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
        self.devicenames.remove(secondarydev)
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testSelectAll(self):
        """Test Selecting all devices"""
        self._goToDeviceList() 
        self.waitForElement("id=setSelectAll")
        self.selenium.click("id=setSelectAll")
        do_command_byname(self.selenium, "assertChecked", "evids:list")
        self.selenium.click("id=setSelectNone")
        do_command_byname(self.selenium, "assertNotChecked", "evids:list")

    def testSetPriority(self):
        """Test Setting Priority to the Highest"""
        curtarget = secondarydev
        self._goToDeviceList() 
        self._clickDeviceInList(curtarget)
        self.selenium.click("link=Set Priority...")
        self.waitForElement("setProductionState:method")
        self.selenium.select('priority', 'value=5')
        self.selenium.click("setProductionState:method")
        self.selenium.do_command("waitForText",
                ['id=messageSlot', 'Priority set to Highest'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertTextPresent', ['Highest',])

    def testSetProductionState(self):
        """Test Setting Production state to the Test"""
        curtarget = secondarydev
        self._goToDeviceList() 
        self._clickDeviceInList(curtarget)
        self.selenium.click("link=Set Production State...")
        self.waitForElement("setProductionState:method")
        self.selenium.select('state', 'value=400')
        self.selenium.click("setProductionState:method")
        self.selenium.do_command("waitForText",
                ['id=messageSpan'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertTextPresent', ['Test'])

    def testMoveClass(self):
        """Test Moving Class to /Server/testingString"""
        curtarget = secondarydev
        self._addSubClass()
        self._goToDeviceList() 
        self._clickDeviceInList(curtarget)
        self.selenium.click("link=Move to Class...")
        self.waitForElement("moveDevicesToClass:method")
        self.selenium.select('moveTarget', 'label=/Server/testingString')
        self.selenium.click("moveDevicesToClass:method")
        self.selenium.do_command("waitForText",
                ['id=messageSlot', 'Devices moved to /Server/testingString'])
        self.waitForElement("name=evids:list " + curtarget)
        self.waitForElement("link=/Server/testingString")
        self.selenium.do_command('assertElementPresent',
                ['link=/Server/testingString'])
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("name=evids:list " + curtarget)
        self.waitForElement("link=/Server/testingString")
        self.selenium.do_command('assertElementPresent',
                ['link=/Server/testingString'])
        self._deleteSubClass()

    def testSetGroups(self):
        """Test Setting the group to testingString"""
        curtarget = secondarydev
        self._goToGroupsAddOrganizer()
        self._goToDeviceList() 
        self._clickDeviceInList(curtarget)
        self.selenium.click("link=Set Groups...")
        self.waitForElement("setGroups:method")
        self.selenium.select('groupPaths', 'value=/testingString')
        self.selenium.click("setGroups:method")
        self.selenium.do_command("waitForElementPresent",
                ['id=messageSpan'])
        self.goToDevice(curtarget)
        self.selenium.do_command('assertElementPresent', ['link=/testingString'])
        self._goToGroupsDeleteOrganizer()

if __name__ == "__main__":
   unittest.main()

