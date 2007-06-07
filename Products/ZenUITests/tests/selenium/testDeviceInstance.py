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

from selTestBase import selTestBase

class DeviceInstanceTest(selTestBase):
    """
    Perform tests on adding, editing, and deleting devices.
    """
    
    def testSingleDevice(self, deviceIp="tilde.zenoss.loc", classPath="/Discovered"):
        """
        Runs tests on the Add Device page.
        """
        # Device is added and you are on device page
        self.waitForElement("link=Add Device")
        self.selenium.click("link=Add Device")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("loadDevice:method")
        self.selenium.type("deviceName", deviceIp)
        self.selenium.select("devicePath", "label=" + classPath)
        self.selenium.click("loadDevice:method")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=" + deviceIp)
        self.selenium.click("link=" + deviceIp)
        self.selenium.wait_for_page_to_load("30000")
   
        # Edit Device
        self.waitForElement("link=OS")
        self.selenium.click("link=OS")
        self.selenium.wait_for_page_to_load("30000")
        
        #self.doIpInterface()
        #self.doOSProcess()
        #self.doFileSystem()
        import pdb
        pdb.set_trace()
        self.doIpRoute()
   
        # Delete the Device
        self.waitForElement("link=Delete Device...")
        self.selenium.click("link=Delete Device...")
        self.waitForElement("dialog_cancel")
        self.selenium.click("deleteDevice:method")
        self.selenium.wait_for_page_to_load("30000")
        
    
        
    # Add, Modify, and Delete an IpInterface
    def doIpInterface(self):
        self.addDialog(addType="IpInterfaceaddIpInterface", addMethod="addIpInterface:method", fieldId="new_id")
        # future: enter stuff in fields
        # Delete the ipinterface
        self.waitForElement("//div/div[2]/ul/li[1]/a")
        self.selenium.click("//div/div[2]/ul/li[1]/a")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        self.selenium.wait_for_page_to_load("30000")
        
    # Add, Modify, and Delete an OSProcess
    def doOSProcess(self):
        self.addDialog(addType="link=Add OSProcess...")
        # future: enter stuff in fields
        # Delete OSProcess
        self.waitForElement("link=Delete")
        self.selenium.click("link=Delete")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        self.selenium.wait_for_page_to_load("30000")
        
    # Add, Modify, and Delete a FileSystem
    def doFileSystem(self):
        self.addDialog(addType="link=Add File System...")
        #future: enter stuff in fields
        #Delete Filesystem
        self.waitForElement("//div/div[2]/ul/li[1]/a")
        self.selenium.click("//div/div[2]/ul/li[1]/a")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        
    # Add, Modify, and Delete an IP Route
    def doIpRoute(self):
        self.addDialog(addType="link=Add Route...", fieldId2="nexthopid", testData="127.0.0.1/8")
        
        self.deleteDialog(deleteType="IpRouteEntrydeleteIpRouteEntries",
                          deleteMethod="deleteIpRouteEntries:method",
                          pathsList="componentNames:list",
                          form_name="ipRouteEntryListForm",
                          stringVal="127.0.0.1/8")
        
        
if __name__ == "__main__":
    unittest.main()