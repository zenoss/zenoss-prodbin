/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
*/
package loc.zenoss.testcases.ITInfrastructure.WindowsServices;

import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.WinService;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class AddingWindowsServices {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3441;
	private static String testCaseResult = "f"; //Fail by default
		
	@BeforeClass
	 public static void setUpBeforeClass() throws Exception {
		 selenese = new SeleneseTestCase();
	     sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,
	 			ZenossConstants.browser, ZenossConstants.testedMachine)  {
	        		public void open(String url) {
	        			commandProcessor.doCommand("open", new String[] {url,"true"});
	        		}     	};	   
	        		sClient.start();
			sClient.deleteAllVisibleCookies();
			
		}

		@AfterClass
		public static void tearDownAfterClass() throws Exception {
			sClient.stop();
			TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
		}

		
		@Before
		public void setUp() throws Exception {
			 
		}

		@After
		public void tearDown() throws Exception {
		}

		@Test
		public void addWindowsServices() throws Exception{
		
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variable for testing OrganizerName and WinServiceName
			String orgName = "TestOrganizer";
			String servName = "TestService";
			
			// Go to Dashboard > Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			// Wait for Windows Services link and click on it
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("link=Windows Services")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("link=Windows Services");
			sClient.waitForPageToLoad("30000");
			
			// Add Service Organizer
			WinService.addServiceOrganizer(orgName, sClient);
			
			// Add Service to organizer
            WinService.addService(servName, orgName, sClient);
			
            //Click service from the services list
			sClient.mouseDownAt("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + servName + "']", "");
			sClient.mouseUp("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + servName + "']");
			
			//Clicks to verify expected UI is present: Name, Description, Service Keys, Enable Monitoring?, Failure Event Severity, Mornitored Start Modes
			Thread.sleep(10000);
			sClient.click("//input[@id='nameTextField']");
			sClient.click("//input[@id='descriptionTextField']");
			sClient.click("//textarea[@id='serviceKeysTextField']");
			sClient.click("//label[@class='x-form-cb-label' and @for='ext-comp-1101' and text()='Set Local Value:']");
			sClient.click("//input[@id='ext-comp-1103']");
			sClient.click("//label[@class='x-form-cb-label' and text()='Inherit Value \"No\" from Services']");
			sClient.click("//label[@class='x-form-cb-label' and @for='ext-comp-1109' and text()='Set Local Value:']");
			sClient.click("//input[@id='ext-comp-1111']");
			sClient.click("//label[@class='x-form-cb-label' and text()='Inherit Value \"Critical\" from Services']");
			sClient.click("//table[@class='x-table-layout']//span[text()='Available']");
			testCaseResult = "p";
		}

}
