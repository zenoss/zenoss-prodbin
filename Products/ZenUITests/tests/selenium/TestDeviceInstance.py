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

from SelTestBase import SelTestBase

class TestDeviceInstanceBase(SelTestBase):
    """Base class for performing tests on specific device instances."""
    
    def setUp(self):
        """Customized setUp for device instance tests."""
        
        SelTestBase.setUp(self)
        
        self.addDevice()
        self.waitForElement("link=OS")
        self.selenium.click("link=OS")
        self.selenium.wait_for_page_to_load("30000")
        
    def tearDown(self):
        """Customized tearDown for device instance tests."""
        
        self.deleteDevice()
        SelTestBase.tearDown(self)
    
        
class TestDeviceInstanceOsTab(TestDeviceInstanceBase):
    """Test additon, editing, and deletion of IpInterface, IpRouteEntry, etc."""
    
    def testIpInterface(self):
        """Add, edit, and delete an Ip Interface under a specific device."""
        
        self.addDialog(addType="IpInterfaceaddIpInterface", addMethod="addIpInterface:method",
                       new_id=("text", "testingString")
                      )
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
        self.selenium.wait_for_page_to_load("30000")
        
        self.assert_(not self.selenium.is_element_present("link=testingString2"))
        
    def testOSProcess(self):
        """Add, edit, and delete an OS Process under a specific device."""
        
        self.addDialog(addType="link=Add OSProcess...", new_id=("text", "testingString"))
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
        self.selenium.wait_for_page_to_load("30000")
        
        self.assert_(not self.selenium.is_element_present("link=testingString2"))
        
    def testFileSystem(self):
        """Add, edit, and delete a File System under a sepcific device."""
        
        self.addDialog(addType="link=Add File System...", new_id=("text", "testingString"))
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
        self.selenium.wait_for_page_to_load("30000")
        
        self.assert_(not self.selenium.is_element_present("link=testingString2"))
        
    def testIpRoute(self):
        """Add and delete an IP Route under a sepcific device (no editing available)."""
        
        self.addDialog(addType="link=Add Route...", new_id=("text", "127.0.0.1/8"),
                       nexthopid=("text", "127.0.0.1"), routeproto=("select", "label=local"),
                       routetype=("select", "label=direct")
                      )
        self.assert_(self.selenium.is_text_present("127.0.0.1 (None)"))
        
        self.deleteDialog(deleteType="IpRouteEntrydeleteIpRouteEntries",
                          deleteMethod="deleteIpRouteEntries:method",
                          pathsList="componentNames:list",
                          form_name="ipRouteEntryListForm",
                          testData="127.0.0.1/8")
        self.assert_(not self.selenium.is_text_present("127.0.0.1 (None)"))
    
    def testIpService(self):
        """Add, edit, and delete an Ip Service under a sepcific device."""
        
        self.addDialog(addType="link=Add IpService...", new_id=("text", "1234"),
                       port=("text", "1234"), protocol=("select", "label=tcp")
                      )
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
        """Add, edit, and delete a Win Service under a sepcific device."""
        
        self.addDialog(addType="link=Add WinService...", new_id=("text", "testingString"),
                       description=("text", "testingString")
                      )
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
        
class TestDeviceInstanceManageDevice(TestDeviceInstanceBase):
    """Test functionality related to managing the device itself."""
        
    def testChangeDeviceClass(self):
        """Test changing the device class of a device."""
        
        self.selenium.click("link=Change Class...")
        
        self.waitForElement("moveDevices:method")
        self.selenium.select("moveTarget", "label=/Discovered")
        self.selenium.click("moveDevices:method")
        self.selenium.wait_for_page_to_load("30000")
        
        self.assert_(self.selenium.is_element_present("link=Discovered"))
        self.selenium.click("link=build.zenoss.loc")
        
        
    def testRenameDevice(self):
        """Test renaming a device."""
        
        self.selenium.click("link=Rename Device...")
        
        self.waitForElement("dialog_submit")
        self.selenium.type("new_id", "testDevice")
        self.selenium.click("dialog_submit")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_element_present("link=testDevice"))
        
    def testResetIP(self):
        """Test setting a new IP address for a device."""
        
        self.selenium.click("link=Reset IP...")
        
        self.waitForElement("dialog_submit")
        self.selenium.type("new_id", "1.2.3.4")
        self.selenium.click("dialog_submit")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_text_present("1.2.3.4"))
        
    def testLockDevice(self):
        """Test locking a device against deletes and updates."""
        
        # First, test lock against updates (and deletes).
        self.selenium.click("link=Lock...")
        self.waitForElement("dialog_cancel")
        self.selenium.click("lockFromUpdates:method")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_element_present("//img[@src='locked-update-icon.png']"))
        self.assert_(self.selenium.is_element_present("//img[@src='locked-delete-icon.png']"))
        
        self.selenium.click("link=Lock...") # Unlocking the device now.
        self.waitForElement("dialog_cancel")
        self.selenium.click("unlock:method")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(not self.selenium.is_element_present("//img[@src='locked-update-icon.png']"))
        self.assert_(not self.selenium.is_element_present("//img[@src='locked-delete-icon.png']"))
        
        # Then, test lock against deletes only.
        self.selenium.click("link=Lock...")
        self.waitForElement("dialog_cancel")
        self.selenium.click("lockFromDeletion:method")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(self.selenium.is_element_present("//img[@src='locked-delete-icon.png']"))
        
        self.selenium.click("link=Lock...") # Unlocking the device now.
        self.waitForElement("dialog_cancel")
        self.selenium.click("unlock:method")
        self.selenium.wait_for_page_to_load("30000")
        self.assert_(not self.selenium.is_element_present("//img[@src='locked-delete-icon.png']"))
        
        
if __name__ == "__main__":
    unittest.main()