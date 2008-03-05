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

class TestCreateZenpack(SelTestBase):
    """Defines a class that runs tests on creating and Install Zenpacks"""

    def _createZenpack(self):
        self.waitForElement("link=Settings")
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("link=ZenPacks")
        self.selenium.click("link=ZenPacks")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=testingPack"):
            self._deleteZenpack()
        self.addDialog("ZenPacklistaddZenPack",new_id=("text", "testingPack"),
                package=("text", "testpackage"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteZenpack(self):
        """Deletes the testing Zenpack""" 
        self.waitForElement("link=Settings")
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("link=ZenPacks")
        self.selenium.click("link=ZenPacks")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("ZenPacklistremoveZenPack",
                "manage_removeZenPacks:method", pathsList="ids:list",
                form_name="zenPackList", testData="testingPack")
        self.selenium.wait_for_page_to_load(self.WAITTIME)


    def testCreateZenpack(self):
        """Run tests on the ZenPackManager page"""
        self._createZenpack()
        self._deleteZenpack()
        


if __name__ == "__main__":
    unittest.main()
