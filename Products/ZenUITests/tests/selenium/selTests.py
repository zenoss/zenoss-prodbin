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
# Contained below are a series of Selenium test functions that
# test Zenoss functions to make sure they are in working order.
#
# Adam Modlin
#
import unittest, time, re
import jsUtils
import sys

from selenium import selenium
from TimeoutException import TimeoutException

SLEEPTIME   =   2
USER        =   "admin"
PASS        =   "zenoss"
HOST        =   "seltest1"

class selTests(unittest.TestCase):
    def setUp(self):
        """Run at the start of each test.
         """
        self.verificationErrors = []
        self.selenium = selenium("localhost", 4444, "*firefox", "http://seltest1:8080")
        self.selenium.start()
        self.login()
    
    def tearDown(self):
        """Run at the end of each test.
        """
        self.logout()
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
        
    def login (self):
        """Logs selenium into the Zenoss Instance.
        """
        self.selenium.open("/zport/acl_users/cookieAuthHelper/login_form?came_from=http%%3A//%s%%3A8080/zport/dmd" %HOST)
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("__ac_password")
        self.selenium.type("__ac_name", USER)
        self.selenium.type("__ac_password", PASS)
        self.selenium.click("//input[@value='Submit']")
        self.selenium.wait_for_page_to_load("30000")
        
    def logout(self):
        """Logs out of the Zenoss instance
        """
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("link=Logout")
        self.selenium.click("link=Logout")
        
    def type_keys(self, locator, keyseq="testingString"):
        """Because Selenium lies about what functions it actually has.
        """
        for x in keyseq:
            self.selenium.key_press(locator, str(ord(x)))

#################################################################
#                   Tester functions:                           #
#                                                               #
#                       testSystems                             #
#                       testGroups                              #
#                       testLocations                           #
#                       testReports                             #
#                       testEvents                              #
#                       testAddDeleteDevice                     #
#                       testDevices                             #
#                                                               #
#################################################################

    def testAll(self):
        """Run all the tests.
        """
        #self._testEvents()              #working
        #self._testDevices()             #working
        #self._testServices()           #unimplemented
        #self._testProcesses()          #unimplemented
        #self._testProducts()           #unimplemented
        
        #self._testSystems()             #working
        #self._testGroups()              #working
        #self._testLocations()           #working
        #self._testReports()             #working
        
        #self._testMonitors()           #unimplemented
        #self._testMibs()               #unimplemented
        self._testAddEditDeleteDevice(deviceIp="tilde.zenoss.loc", classPath="/Discovered")     #working
        #self._testEventManager()       #unimplemented
        #self._testSettings()           #unimplemented
        
################################################        
        
    def _testEventConsole(self):
        """Run tests on the Event Console page.
        """
        
    def _testDeviceList(self):
        """Run tests on the Device List page.
        """
        
    def _testNetworks(self):
        """Run tests on the Networks page.
        """
        
################################################        
        
    def _testEvents(self):
        """Run tests on the Events page.
        """
        self.waitForElement("link=Events")
        self.selenium.click("link=Events")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.deleteDialog(form_name="subclasses")
        #self.addDialog(addType="EventMappinglistaddInstance")
        #self.moveEventClassMappings()   This is currently broken
        #self.deleteDialog(deleteType="EventMappinglistremoveInstances", deleteMethod="removeInstances:method",
        #                            pathsList="ids:list", form_name="mappings") 

    def _testDevices(self):
        """Run tests on the Devices page
        """
        self.waitForElement("link=Devices")
        self.selenium.click("link=Devices")
        self.waitForElement("link=Templates")
        self.selenium.click("link=Templates")
        self.addDialog(addType="TemplatesaddTemplate")
        self.deleteDialog(deleteType="TemplatesdeleteTemplates", deleteMethod="manage_deleteRRDTemplates:method",
                            pathsList="ids:list", form_name="templates")        

    def _testServices(self):
        """Run tests on the Services page.
        """
        self.waitForElement("link=Services")
        self.selenium.click("link=Services")
        self.selenium.wait_for_page_to_load("30000")
        ##      Add a new Organizer
        self.addDialog()
        self.selenium.wait_for_page_to_load("30000")
        ##      Add a Service and then delete it
        self.addDialog(addType="ServicelistaddServiceClass", addMethod="manage_addServiceClass:method", fieldId="id")
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog(deleteType="ServicelistremoveServiceClasses", deleteMethod="removeServiceClasses:method",
                            pathsList="ids:list", form_name="services")
        self.selenium.wait_for_page_to_load("30000")
        ##      Add an IP Service and then delete it
        self.addDialog(addType="ServicelistaddIpServiceClass", addMethod="manage_addIpServiceClass:method", fieldId="id")
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog(deleteType="ServicelistremoveServiceClasses", deleteMethod="removeServiceClasses:method",
                            pathsList="ids:list", form_name="services")
        self.selenium.wait_for_page_to_load("30000")
    
    def _testProcesses(self):
        """Run tests on the Processs page.
        """

    def _testProducts(self):
       """Run tests on the Products page.
       """

################################################

    def _testSystems(self):
        """Run tests on the Systems page.
        """
        self.waitForElement("link=Systems")
        self.selenium.click("link=Systems")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load("30000")
        
    def _testGroups(self):
        """Run tests on the Groups page.
        """
        self.waitForElement("link=Groups")
        self.selenium.click("link=Groups")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load("30000")
        
    def _testLocations(self):
        """Run tests on the Locations page.
        """
        self.waitForElement("link=Locations")
        self.selenium.click("link=Locations")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog()
        self.selenium.wait_for_page_to_load("30000")
        
    def _testReports(self):
        """Run tests on the Reports page.
        """
        self.waitForElement("link=Reports")
        self.selenium.click("link=Reports")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog(addType="ReportClasslistaddReportClass")
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog(deleteType="ReportClasslistdeleteReportClasses", form_name="reportClassForm")
        self.selenium.wait_for_page_to_load("30000")
        
################################################        
        
    def _testMonitors(self):
        """Run tests on the Monitors page.
        """

    def _testMibs(self):
        """Run tests on the Mibs page
        """
        
    def _testAddEditDeleteDevice(self, deviceIp, classPath):
        """Runs tests on the Add Device page.
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
        
        # Add, Modify, and Delete an IpInterface
        self.addDialog(addType="IpInterfaceaddIpInterface", addMethod="addIpInterface:method", fieldId="new_id")
        self.selenium.wait_for_page_to_load("30000")
        self.waitForElement("zmanage_editProperties:method")
        self.selenium.click("zmanage_editProperties:method")
        # future: enter stuff in fields
        # Delete the ipinterface
        self.waitForElement("link=Delete")
        self.selenium.click("link=Delete")
        self.waitForElement("manage_deleteComponent:method")
        self.selenium.click("manage_deleteComponent:method")
        self.selenium.wait_for_page_to_load("30000")

        # Add OSProcess
        self.addDialog(addType="link=Add OSProcess...")
        self.selenium.wait_for_page_to_load("30000")
        # future: enter stuff in fields
        # Delete OSProcess
        self.waitForElement("link=Delete")
        self.selenium.click("link=Delete")
        self.waitForElement("manage_deleteComponent:method")
        self.selenium.click("manage_deleteComponent:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # Add Filesystem
        self.addDialog(addType="link=Add File System...")
        #future: enter stuff in fields
        #Delete Filesystem
        self.waitForElement("link=Delete")
        self.selenium.click("link=Delete")
        self.waitForElement("manage_deleteComponent:method")
        self.selenium.click("manage_deleteComponent:method")
        self.selenium.wait_for_page_to_load("30000")
        
        # Add IP Route
        self.addDialog(addType="link=Add Route...", fieldId2="nexthopid", overrideString="127.0.0.1/8")
        
        # Delete the Device
        self.waitForElement("link=Delete Device...")
        self.selenium.click("link=Delete Device...")
        self.waitForElement("deleteDevice:method")
        self.selenium.click("deleteDevice:method")
        self.selenium.wait_for_page_to_load("30000")
        
    def _testEventManager(self):
        """Run tests on the Event Manager page.
        """
        
    def _testSettings(self):
        """Run tests on the Settings page.
        """


#################################################################
#                                                               #
#                   Utility functions for all                   #
#                   of the tester functions                     #
#                                                               #
#################################################################

    def addUser(self, username="testingString", email="nosuchemail@zenoss.com", defaultAdminRole="Administrator", ):
        """Test the addUser functionality
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
        self.waitForElement("password")
        self.type_keys("password")
        self.waitForElement("sndpassword")
        self.type_keys("sndpassword")
        self.waitForElement("manage_editUserSettings:method")
        self.selenium.click("manage_editUserSettings:method")

    def addDialog(self, addType="OrganizerlistaddOrganizer", addMethod="dialog_submit", fieldId="new_id",
                    fieldId2=None, overrideString="testingString"):
        """Test the addDialog functionality.
        """
        self.selenium.click(addType)
        #time.sleep(1)
        self.type_keys(fieldId, overrideString)
        if fieldId2 != None:
            self.waitForElement(fieldId2)
            self.type_keys(fieldId2, overrideString)
        self.selenium.click(addMethod)
        #time.sleep(1)
        
    def deleteDialog(self, deleteType="OrganizerlistremoveOrganizers", deleteMethod="manage_deleteOrganizers:method", 
                        pathsList="organizerPaths:list", form_name="subdeviceForm"):
        """Test the deleteOrganizer functionality.
        """
        self.waitForElement(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        self.selenium.click(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        self.waitForElement(deleteType)
        self.selenium.click(deleteType)
        self.waitForElement(deleteMethod)
        self.selenium.click(deleteMethod)

    def moveEventClassMappings(self, pathsList="ids:list", form_name="mappings", moveTo="/Unknown"):
        """Test moving an EventClassMapping to /Unknown.
        """
        self.waitForElement(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        self.selenium.click(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        self.waitForElement("EventmappinglistmoveInstances")
        self.selenium.click("EventMappinglistmoveInstances")
        self.waitForElement("moveInstances:method")
        self.selenium.select("moveTarget", moveTo)
        self.selenium.click("moveInstances:method")
    
    def waitForElement(self, locator, timeout=15):
        i = 0
        try:
            while not self.selenium.is_element_present(locator):
                time.sleep(1)
                i += 1
                if i >= timeout:
                    raise TimeoutException("Timed out waiting for " + locator)
        except TimeoutException, e:
            import traceback
            traceback.print_exc()
            self.selenium.stop()
            raise e
            
        
if __name__ == "__main__":
    unittest.main()
