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

from SelTestBase import SelTestBase,TARGET

class TestDeviceInstanceBase(SelTestBase):
    """Base class for performing tests on specific device instances"""

    def setUp(self):
        """Customized setUp for device instance tests"""

        SelTestBase.setUp(self)

        self.addDevice()

    def tearDown(self):
        """Customized tearDown for device instance tests"""

        self.goToDevice()
        self.deleteDevice()
        SelTestBase.tearDown(self)


class TestDeviceList(TestDeviceInstanceBase):
    """Test the device list"""

    def _goToDeviceList(self):
        self.waitForElement("link=Device List")
        self.selenium.click("link=Device List")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def testSelectAll(self):
        """Test Selecting all devices"""
        self._goToDeviceList() 
        self.waitForElement("id=setSelectAll")
        self.selenium.click("id=setSelectAll")
        do_command_byname(self.selenium, "assertChecked", "evids:list")
        self.selenium.click("id=setSelectNone")
        do_command_byname(self.selenium, "assertNotChecked", "evids:list")

    def xtestSelectNone(self):
        """Test Deselcting all devices"""
        self._goToDeviceList()
        self.testSelectAll()
        self.waitForElement("id=setSelectNone")
        self.selenium.click("id=setSelectNone")


if __name__ == "__main__":
   unittest.main()

