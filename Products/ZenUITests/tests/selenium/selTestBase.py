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

import sys, time, re
import unittest
from selTestUtils import *

from selenium import selenium

USER        =   "admin"
PASS        =   "zenoss"
HOST        =   "seltest1"

class selTestBase(unittest.TestCase):
    """
    Base class for Zenoss Selenium tests.
    All test classes should inherit this.
    """
	
    def setUp(self):
        """
        Run at the start of each test.
        """
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*firefox", "http://seltest1:8080")
        self.selenium.start()
        self.login()
    
    def tearDown(self):
        """
        Run at the end of each test.
        """
        self.logout()
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)



#################################################################
#                                                               #
#                   Utility functions for all                   #
#                   of the tester functions                     #
#                                                               #
#################################################################

    def login (self):
        """
        Logs selenium into the Zenoss Instance.
        """
        self.selenium.open("/zport/acl_users/cookieAuthHelper/login_form?came_from=http%%3A//%s%%3A8080/zport/dmd" %HOST)
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("__ac_password")
        self.selenium.type("__ac_name", USER)
        self.selenium.type("__ac_password", PASS)
        self.selenium.click("//input[@value='Submit']")
        self.selenium.wait_for_page_to_load("30000")
        
    def logout(self):
        """
        Logs out of the Zenoss instance
        """
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Logout")
        self.selenium.click("link=Logout")
        
    def addDevice(self, deviceIp="tilde.zenoss.loc", classPath="/Discovered"):
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
        
    def deleteDevice(self):
        # Delete the Device
        self.waitForElement("link=Delete Device...")
        self.selenium.click("link=Delete Device...")
        self.waitForElement("dialog_cancel")
        self.selenium.click("deleteDevice:method")
        self.selenium.wait_for_page_to_load("30000")

    def addUser(self, username="testingString", email="nosuchemail@zenoss.com", defaultAdminRole="Administrator", ):
        """
        Test the addUser functionality
        """
        self.waitForElement("link=Settings")
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load("30000")
        self.selenium.click("link=Users")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("UserlistaddUser")
        self.addDialog(addType="UserlistaddUser", fieldId2="email")
        self.selenium.click("link=testingString")
        self.selenium.wait_for_page_to_load("30000")
        self.selenium.add_selection("roles:list", "label=Manager")
        self.selenium.remove_selection("roles:list", "label=ZenUser")
        self.waitForElement("manage_editUserSettings:method")
        self.type_keys("password")
        self.type_keys("sndpassword")
        self.selenium.click("manage_editUserSettings:method")

    def addDialog(self, addType="OrganizerlistaddOrganizer", addMethod="dialog_submit", fieldId="new_id",
                    fieldId2=None, testData="testingString"):
        """
        Test the addDialog functionality.
        """
        self.waitForElement(addType)
        self.selenium.click(addType)
        self.waitForElement("dialog_cancel")
        #self.type_keys(fieldId, testData)
        self.selenium.type(fieldId, testData)
        if fieldId2 != None:
            self.waitForElement(fieldId2)
            #self.type_keys(fieldId2, testData)
            self.selenium.type(fieldId2, testData)
        self.selenium.click(addMethod)
        self.selenium.wait_for_page_to_load("30000")
        
    def deleteDialog(self, deleteType="OrganizerlistremoveOrganizers", deleteMethod="manage_deleteOrganizers:method", 
                        pathsList="organizerPaths:list", form_name="subdeviceForm", testData="testingString"):
        """
        Test the deleteOrganizer functionality.
        """
        testData = slashToUnder(testData)
        self.waitForElement(getByValue(pathsList, testData, form_name))
        self.selenium.click(getByValue(pathsList, testData, form_name))
        self.waitForElement(deleteType)
        self.selenium.click(deleteType)
        self.waitForElement(deleteMethod)
        self.selenium.click(deleteMethod)
        self.selenium.wait_for_page_to_load("30000")

    
    def waitForElement(self, locator, timeout=15):
        """
        Waits until a given element on a page is present.
        Throws a TimeoutException if too much time has
        passed.
        """
        i = 0
        try:
            while not self.selenium.is_element_present(locator):
                time.sleep(1)
                i += 1
                if i >= timeout:
                    raise TimeoutError("Timed out waiting for " + locator)
        except TimeoutError, e:
            import traceback
            traceback.print_exc()
            self.selenium.stop()
            raise e

        
    def type_keys(self, locator, keyseq="testingString"):
        """
        Because Selenium lies about what functions it actually has.
        """
        for x in keyseq:
            self.selenium.key_press(locator, x)	