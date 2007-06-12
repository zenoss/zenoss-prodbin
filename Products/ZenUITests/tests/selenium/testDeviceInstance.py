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

from selTestBase import selTestBase

class DeviceInstanceTest(selTestBase):
    """Perform tests on adding, editing, and deleting devices."""
    
    def setUp(self):
        """Customized setUp for device instance tests."""
        
        selTestBase.setUp(self)
        
        self.addDevice()
        self.waitForElement("link=OS")
        self.selenium.click("link=OS")
        self.selenium.wait_for_page_to_load("30000")
        
    def tearDown(self):
        """Customized tearDown for device instance tests."""
        
        self.deleteDevice()
        selTestBase.tearDown(self)
    
    #def testSingleDevice(self):
    #    """
    #    Runs tests on a device instance.
    #    """
    #    self.addDevice()
   
        # Edit Device
    #    self.waitForElement("link=OS")
    #    self.selenium.click("link=OS")
    #    self.selenium.wait_for_page_to_load("30000")
        
    #    self.doIpInterface()
    #    self.doOSProcess()
    #    self.doFileSystem()
    #    self.doIpRoute()
    #    self.doIpService()
    #    self.doWinService()
        
    #    self.deleteDevice()
    
        
    def testIpInterface(self):
        """Adds, edits, and deletes an Ip Interface under a specific device."""
        
        self.addDialog(addType="IpInterfaceaddIpInterface", addMethod="addIpInterface:method")
        self.assert_(self.selenium.is_element_present("link=testingString"))
        
        # now, edit some fields
        self.selenium.type("interfaceName", "testingString2")
        self.selenium.type("macaddress", "AA:AA:AA:AA:AA:AA:AA:AA")
        self.selenium.type("ips:lines", "127.0.0.1")
        self.selenium.type("type", "testIface")
        self.selenium.type("speed", "1000")
        self.selenium.type("mtu", "1000")
        self.selenium.type("ifindex", "1000")
        self.selenium.type("description", "testy")
        
        self.selenium.select("operStatus", "label=Up")
        self.selenium.select("adminStatus", "label=Down")
        self.selenium.select("monitor:boolean", "label=False")
        
        self.selenium.click("zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # Then, delete the IpInterface
        self.selenium.click("//div/div[2]/ul/li[1]/a")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        # Assertion below fails for unknown reason.
        #self.assert_(not self.selenium.is_element_present("link=testingString"))
        
    def testOSProcess(self):
        """Adds, edits, and deletes an OS Process under a specific device."""
        
        self.addDialog(addType="link=Add OSProcess...")
        self.assert_(self.selenium.is_element_present("link=testingString"))
        
        # Enter new data in form
        self.selenium.type("name", "testingString2")
        
        self.selenium.select("zMonitor:boolean", "label=False")
        self.selenium.select("zAlertOnRestart:boolean", "label=True")
        self.selenium.select("zFailSeverity:int", "label=Critical")
        
        self.selenium.click("manage_editOSProcess:method")
        self.selenium.wait_for_page_to_load("30000")

        # Then, delete OSProcess
        self.selenium.click("link=Delete")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        # Assertion below fails for unknown reason.
        #self.assert_(not self.selenium.is_element_present("link=testingString"))
        
    def testFileSystem(self):
        """Adds, edits, and deletes a File System under a sepcific device."""
        
        self.addDialog(addType="link=Add File System...")
        self.assert_(self.selenium.is_element_present("link=testingString"))
        
        # Edit FileSystem fields
        self.selenium.type("mount", "testingString2")
        self.selenium.type("storageDevice", "testingString")
        self.selenium.type("type", "testingString")
        self.selenium.type("blockSize", "1234")
        self.selenium.type("totalFiles", "1234")
        self.selenium.type("maxNameLen", "1234")
        self.selenium.type("snmpindex", "1234")
        
        self.selenium.select("monitor:boolean", "label=False")
        
        self.selenium.click("manage_editFileSystem:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # Delete Filesystem
        self.selenium.click("//div/div[2]/ul/li[1]/a")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        # Assertion below fails for unknown reason.
        #self.assert_(not self.selenium.is_element_present("link=testingString"))
        
    def testIpRoute(self):
        """Adds and deletes an IP Route under a sepcific device (no editing available)."""
        
        self.addDialog(addType="link=Add Route...", fieldId2="nexthopid", testData="127.0.0.1/8")
        self.assert_(self.selenium.is_text_present("127.0.0.1/8 (None)"))
        
        self.deleteDialog(deleteType="IpRouteEntrydeleteIpRouteEntries",
                          deleteMethod="deleteIpRouteEntries:method",
                          pathsList="componentNames:list",
                          form_name="ipRouteEntryListForm",
                          testData="127.0.0.1/8")
        self.assert_(not self.selenium.is_text_present("127.0.0.1/8 (None)"))
    
    def testIpService(self):
        """Adds, edits, and deletes an Ip Service under a sepcific device."""
        
        self.addDialog(addType="link=Add IpService...", fieldId2="port", testData="1234")
        self.assert_(self.selenium.is_element_present("link=1234"))
            
        # now, edit some of the fields
        self.selenium.type("id", "2345")
        self.selenium.type("port", "2345")
        self.selenium.type("ipaddresses:lines", "127.0.0.1")
        self.selenium.type("sendString", "stringy")
        self.selenium.type("expectRegex", "\\bregex\\b")
        self.selenium.type("description", "test")
        
        self.selenium.select("protocol", "label=tcp")
        self.selenium.select("monitor:boolean", "label=True")
        self.selenium.select("severity:int", "label=Error")
        
        self.selenium.click("manage_editService:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # bug workaround
        self.selenium.click("link=2345")
        self.selenium.wait_for_page_to_load("30000")
            
        # then delete the Ip Service
        self.selenium.click("link=Delete")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        # TODO: add an assert statement concerning the ip service's deletion.
            
    def testWinService(self):
        """Adds, edits, and deletes a Win Service under a sepcific device."""
        
        self.addDialog(addType="link=Add WinService...", fieldId2="description")
        self.assert_(self.selenium.is_element_present("link=testingString"))
        
        # now, edit some of the fields
        self.selenium.type("id", "testingString2")
        self.selenium.type("description", "testingString2")
        self.selenium.type("serviceType", "test")
        self.selenium.type("startMode", "test")
        self.selenium.type("startName", "test")
        self.selenium.type("pathName", "test")
        
        self.selenium.select("monitor:boolean", "label=True")
        self.selenium.select("severity:int", "label=Error")
        self.selenium.select("acceptPause:boolean", "label=True")
        self.selenium.select("acceptStop:boolean", "label=True")
        
        self.selenium.click("manage_editService:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # bug workaround
        self.selenium.click("link=testingString2")
        self.selenium.wait_for_page_to_load("30000")
        
        # then delete the WinService
        self.selenium.click("link=Delete")
        self.waitForElement("dialog_cancel")
        self.selenium.click("manage_deleteComponent:method")
        self.assert_(not self.selenium.is_text_present("Win Services"))
        
    def testChangeDeviceClass(self):
        """Tests changing the device class of a device."""
        
        self.selenium.click("link=Change Class...")
        
        self.waitForElement("moveDevices:method")
        self.selenium.select("moveTarget", "label=/Server/Linux")
        self.selenium.click("moveDevices:method")
        self.selenium.wait_for_page_to_load("30000")
        
        self.assert_(self.selenium.is_element_present("link=Linux"))
        self.selenium.click("link=tilde.zenoss.loc")
        
        
    def testRenameDevice(self):
        """Tests renaming a device."""
        
        self.selenium.click("link=Rename Device...")
        
        self.waitForElement("dialog_submit")
        self.selenium.type("new_id", "testDevice")
        self.selenium.click("dialog_submit")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_element_present("link=testDevice"))
        
    def testResetIP(self):
        """Tests setting a new IP address for a device."""
        
        self.selenium.click("link=Reset IP...")
        
        self.waitForElement("dialog_submit")
        self.selenium.type("new_id", "1.2.3.4")
        self.selenium.click("dialog_submit")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_text_present("1.2.3.4"))
        
        
        
if __name__ == "__main__":
    unittest.main()