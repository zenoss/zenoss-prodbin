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
# Contained below is the base class for Zenoss Selenium tests.
#
# Adam Modlin and Nate Avers
#

import time, os
import unittest
from util.selTestUtils import *

from util.selenium import selenium


### BEGIN GLOBAL DEFS ###
HOST        =   "nightlytest.zenoss.loc"         # Zenoss instance to test
USER        =   "admin"                 # Username for HOST
PASS        =   "zenoss"                # Password for HOST
SERVER      =   "nightlytest.zenoss.loc"         # Hosts the selenium jar file
TARGET      =   "nightlytest.zenoss.loc"         # Added/deleted in HOST
BROWSER     =   "*firefox"             # Can also be "*iexplore"
WAITTIME    =   "60000"                 # Time to wait for page loads in milliseconds
### END GLOBAL DEFS ###

# Check for local defs
here = lambda x:os.path.join(os.path.dirname(__file__), x)
if os.path.exists(here('_seleniumtestdata.py')):
    from _seleniumtestdata import *

class SelTestBase(unittest.TestCase):
    """Base class for Zenoss Selenium tests.
        All test classes should inherit this."""
	
    def setUp(self):
        """Run at the start of each test"""
        self.WAITTIME = WAITTIME
        self.verificationErrors = []
        self.selenium = selenium(SERVER, 4444, BROWSER, "http://%s:8080" %HOST)
        self.selenium.start()
        self.login()
    
    def tearDown(self):
        """Run at the end of each test"""
        self.logout()
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)



#################################################################
#                                                               #
#                   Utility functions for all                   #
#                   of the tester functions                     #
#                                                               #
#################################################################

    # Function borrowed from example code on openqa.org.
    # Reference:
    #   http://svn.openqa.org/fisheye/viewrep/~raw,r=HEAD/selenium-rc/
    #   trunk/clients/python/test_default_server.py
    def login (self):
        """Logs selenium into the Zenoss Instance"""
        self.selenium.open("/zport/acl_users/cookieAuthHelper/login_form?came_from=http%%3A//%s%%3A8080/zport/dmd" %HOST)
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("__ac_password")
        self.selenium.type("__ac_name", USER)
        self.selenium.type("__ac_password", PASS)
        self.selenium.click("//input[@name='submit']")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def logout(self):
        """Logs out of the Zenoss instance"""
        self.waitForElement("link=Logout")
        self.selenium.click("link=Logout")
        
    # FAILS if device at deviceIp is already present in Zenoss test target.
    # Does it?  Looks to me like it attempts to delete it.  -jrs
    def addDevice(self, deviceIp=TARGET, classPath="/Server/Linux"):
        """Adds a test target device to Zenoss"""
        # First, make sure the device isn't already in the system.
        self.waitForElement("query")
        self.selenium.type("query", deviceIp)
        self.selenium.submit("searchform")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=%s" %deviceIp):
            self.selenium.click("link=%s" %deviceIp)
            self.selenium.wait_for_page_to_load(self.WAITTIME)
            self.deleteDevice(deviceIp)
        
        # Then add the device and navigate to its top level page.   
        self.waitForElement("link=Add Device")
        self.selenium.click("link=Add Device")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("loadDevice:method")
        self.selenium.type("deviceName", deviceIp)
        self.selenium.select("devicePath", "label=" + classPath)
        self.selenium.select('discoverProto', 'label=none')
        self.selenium.click("loadDevice:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("link=" + deviceIp)
        self.selenium.click("link=" + deviceIp)
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if not hasattr(self, "devicenames"):
            self.devicenames=[]
        if not deviceIp in self.devicenames:
            self.devicenames.append(deviceIp)
        
    def deleteDevice(self, devname=None):
        """Delete the test target device from Zenoss test instance"""
        if not devname:
            devname = getattr(self, "devname", TARGET)
        self.goToDevice(devname)
        self.waitForElement("link=Delete Device...")
        self.selenium.click("link=Delete Device...")
        self.waitForElement("dialog_cancel")
        self.selenium.click("deleteDevice:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    # Not actually sure where this is used.
    def addUser(self, username="testingString", 
                      email="nosuchemail@zenoss.com", 
                      defaultAdminRole="Administrator", ):
        """Test the addUser functionality"""
        self.waitForElement("link=Settings")
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Users")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("UserlistaddUser")
        self.addDialog(addType="UserlistaddUser", fieldId2="email")
        self.selenium.click("link=testingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.add_selection("roles:list", "label=Manager")
        self.selenium.remove_selection("roles:list", "label=ZenUser")
        self.waitForElement("manage_editUserSettings:method")
        self.type_keys("password")
        self.type_keys("sndpassword")
        self.selenium.click("manage_editUserSettings:method")

    # The textFields dictionary is organized as follows:
    # Keys are the name of the input field.
    # Values are a tuple:
    #   First element is the type of input field (either "text" or "select")
    #   Second element is the value that should be entered in the input field.
    def addDialog(self, addType="OrganizerlistaddOrganizer", addMethod="dialog_submit", **textFields):
        """Fills in an AJAX dialog."""
        
        fieldkeys=textFields.keys()
        fieldkeys.reverse()
        self.waitForElement(addType) # Bring up the dialog.
        self.selenium.click(addType)
        self.waitForElement(addMethod) # Wait till dialog is finished loading.
        for key in fieldkeys: # Enter all the values.
            value = textFields[key]
            if value[0] == "select":
                self.selenium.select(key, value[1])
            elif value[0] == "text":
                self.selenium.type(key, value[1])
                #self.selenium.do_command("setCursorPosition", ["className", "-1"])
                #self.selenium.do_command("keyPress", ["className", r"\08"])
                #self.selenium.do_command("keyPress", ["className", r"\13"])
                #self.waitForElement("xpath=//ul/li[@style='display: list-item;']") 
                #self.selenium.click("css=li.yui-ac-highlight")

        self.selenium.click(addMethod) # Submit form.
        self.selenium.wait_for_page_to_load(self.WAITTIME) # Wait for page refresh.
    def goToDevice(self, deviceName=TARGET):
        self.waitForElement("query")
        self.selenium.type("query", deviceName)
        self.selenium.submit("searchform")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
        
    def addOSProcessClass(self):
        """Adds an os process class"""
        self.selenium.click("link=Processes")
        self.waitForElement("link=Add Process...")
        self.selenium.click("link=Add Process...")
        self.waitForElement("manage_addOSProcessClass:method")
        self.selenium.type("id", "httpd")
        self.selenium.click("manage_addOSProcessClass:method")

    def deleteOSProcessClasses(self):
        """Deletes an OSProcessClass"""
        self.selenium.click("link=Processes")
        self.waitForElement("//input[@value='httpd']")
        self.selenium.click("//input[@value='httpd']")
        self.selenium.click("link=Delete Processes...")
        self.waitForElement("removeOSProcessClasses:method")
        self.selenium.click("removeOSProcessClasses:method")

    def deleteDialog(self, deleteType="OrganizerlistremoveOrganizers", deleteMethod="manage_deleteOrganizers:method", 
                        pathsList="organizerPaths:list", form_name="subdeviceForm", testData="testingString"):
        """Test the deleteOrganizer functionality"""
        # Since Zenoss converts slashes to underscores, do the same.
        testData = testData.replace('/', '_')

        # Find the desired element in a checkbox selection.
        self.waitForElement(getByValue(pathsList, testData, form_name))
        self.selenium.click(getByValue(pathsList, testData, form_name))

        # Bring up the delete dialog.
        self.waitForElement(deleteType)
        self.selenium.click(deleteType)

        # Wait for and click the delete button. Wait for page refresh.
        self.waitForElement(deleteMethod)
        self.selenium.click(deleteMethod)
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    
    def waitForElement(self, locator, timeout=15):
        """Waits until a given element on a page is present.
           Throws a TimeoutException if too much time has
           passed."""
        i = 0.0
        while not self.selenium.is_element_present(locator):
            time.sleep(0.25)
            i += 0.25
            if i >= timeout:
                raise TimeoutError("Timed out waiting for " + locator)

       # Included for historical reasons.
    # This functionality no longer seems to be necessary.
    def type_keys(self, locator, keyseq="testingString"):
        """Because Selenium lies about what functions it actually has"""
        for x in keyseq:
            self.selenium.key_press(locator, x)
