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

from selenium import selenium
import unittest, time, re
import jsUtils

SLEEPTIME   =   2
KEYSEQUENCE =   "testingString"
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
        time.sleep(SLEEPTIME)
        self.selenium.type("__ac_name", USER)
        self.selenium.type("__ac_password", PASS)
        self.selenium.click("//input[@value='Submit']")
        self.selenium.wait_for_page_to_load("30000")
        
    def logout(self):
        """Logs out of the Zenoss instance
        """
        self.selenium.click("link=Logout")
        self.selenium.wait_for_page_to_load("30000")
        
    def type_keys(self, locator):
        """Because Selenium lies about what functions it actually has.
        """
        for x in KEYSEQUENCE:
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
        self._testAddEditDeleteDevice()     #working
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
        time.sleep(SLEEPTIME)
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
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Devices")
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Templates")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog(addType="TemplatesaddTemplate")
        self.deleteDialog(deleteType="TemplatesdeleteTemplates", deleteMethod="manage_deleteRRDTemplates:method",
                            pathsList="ids:list", form_name="templates")        

    def _testServices(self):
        """Run tests on the Services page.
        """
        self.selenium.click("link=Services")
        self.selenium.wait_for_page_to_load("30000")
        ##      Add a new Organizer
        self.addDialog()
        ##      Add a Service and then delete it
        self.addDialog(addType="ServicelistaddServiceClass", addMethod="manage_addServiceClass:method", fieldId="id")
        self.deleteDialog(deleteType="ServicelistremoveServiceClasses", deleteMethod="removeServiceClasses:method",
                            pathsList="ids:list", form_name="services")
        ##      Add an IP Service and then delete it
        self.addDialog(addType="ServicelistaddIpServiceClass", addMethod="manage_addIpServiceClass:method", fieldId="id")
        self.deleteDialog(deleteType="ServicelistremoveServiceClasses", deleteMethod="removeServiceClasses:method",
                            pathsList="ids:list", form_name="services")
    
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
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Systems")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.deleteDialog()
        
    def _testGroups(self):
        """Run tests on the Groups page.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Groups")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.deleteDialog()
        
    def _testLocations(self):
        """Run tests on the Locations page.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Locations")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog()
        self.deleteDialog()
        
    def _testReports(self):
        """Run tests on the Reports page.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Reports")
        self.selenium.wait_for_page_to_load("30000")
        self.addDialog(addType="ReportClasslistaddReportClass")
        self.deleteDialog(deleteType="ReportClasslistdeleteReportClasses", form_name="reportClassForm")
        
################################################        
        
    def _testMonitors(self):
        """Run tests on the Monitors page.
        """

    def _testMibs(self):
        """Run tests on the Mibs page
        """
        
    def _testAddEditDeleteDevice(self):
        """Runs tests on the Add Device page.
        """
        # Device is added and you are on device page
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Add Device")
        self.selenium.wait_for_page_to_load("30000")
        time.sleep(SLEEPTIME)
        self.selenium.type("deviceName", "tilde.zenoss.loc")
        time.sleep(SLEEPTIME)
        self.selenium.select("devicePath", "label=/Discovered")
        time.sleep(SLEEPTIME)
        self.selenium.click("loadDevice:method")
        self.selenium.wait_for_page_to_load("30000")
        time.sleep(15)
        self.selenium.click("link=tilde.zenoss.loc")
        self.selenium.wait_for_page_to_load("30000")
        
        # Edit Device
        self.selenium.click("link=OS")
        self.selenium.wait_for_page_to_load("30000")
        
        ######  Add, Modify, and Delete an IpInterface
        self.addDialog(addType="IpInterfaceaddIpInterface", addMethod="addIpInterface:method", fieldId="new_id")
        self.selenium.wait_for_page_to_load("30000")
        self.selenium.click("zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load("30000")
        # future: enter stuff in fields
        
        #Delete the ipinterface
        self.selenium.click("link=os")
        self.selenium.wait_for_page_to_load("30000")
        self.deleteDialog(deleteType="IpInterfacedeleteIpInterfaces", deleteMethod="deleteIpInterfaces:method", pathsList="componentNames:list", form_name="ipInterfaceListForm")
        self.selenium.click("link=Delete Device...")
        time.sleep(SLEEPTIME)
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
        time.sleep(SLEEPTIME)
        self.selenium.click("link=Settings")
        self.selenium.wait_for_page_to_load("30000")
        self.selenium.clikc("link=Users")
        self.selenium.wait_for_page_to_load("30000")
        time.sleep(SLEEPTIME)
        self.addDialog(addType="UserlistaddUser", fieldId2="email")
        self.selenium.click("link=testingString")
        self.selenium.wait_for_page_to_load("30000")
        sel.add_selection("roles:list", "label=Manager")
        sel.remove_selection("roles:list", "label=ZenUser")
        time.sleep(SLEEPTIME)
        self.type_keys("password")
        time.sleep(SLEEPTIME)
        self.type_keys("sndpassword")
        self.selenium.click("manage_editUserSettings:method")
        self.selenium.wait_for_page_to_load("30000")
        

    def addDialog(self, addType="OrganizerlistaddOrganizer", addMethod="dialog_submit", fieldId="new_id",
                    fieldId2=None):
        """Test the addDialog functionality.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click(str(addType))
        time.sleep(SLEEPTIME)
        self.type_keys(fieldId)
        time.sleep(SLEEPTIME)
        if fieldId2 != None:
            self.type_keys(fieldId2)
        self.selenium.click(str(addMethod))
        time.sleep(SLEEPTIME)
        
    def deleteDialog(self, deleteType="OrganizerlistremoveOrganizers", deleteMethod="manage_deleteOrganizers:method", 
                        pathsList="organizerPaths:list", form_name="subdeviceForm"):
        """Test the deleteOrganizer functionality.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        time.sleep(SLEEPTIME)
        self.selenium.click(str(deleteType))
        time.sleep(SLEEPTIME)
        self.selenium.click(str(deleteMethod))
        time.sleep(SLEEPTIME)
        self.selenium.wait_for_page_to_load("30000")
        
    def moveEventClassMappings(self, pathsList="ids:list", form_name="mappings", moveTo="/Unknown"):
        """Test moving an EventClassMapping to /Unknown.
        """
        time.sleep(SLEEPTIME)
        self.selenium.click(jsUtils.getByValue(pathsList, KEYSEQUENCE, form_name))
        time.sleep(SLEEPTIME)
        self.selenium.click("EventMappinglistmoveInstances")
        time.sleep(SLEEPTIME)
        self.selenium.select("moveTarget", moveTo)
        time.sleep(SLEEPTIME)
        self.selenium.click("moveInstances:method")
        self.selenium.wait_for_page_to_load("30000")
        
if __name__ == "__main__":
    unittest.main()
