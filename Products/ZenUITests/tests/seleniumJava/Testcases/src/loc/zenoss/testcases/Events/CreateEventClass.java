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
package loc.zenoss.testcases.Events;
import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class CreateEventClass {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3103;
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
		public void createEventClass() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variable for testing Organizer Name (Event class)
			String organizerName = "TestClass";
			// Go to Dashboard > Events
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Events");
			sClient.waitForPageToLoad("30000");
			// Wait for Event Classes link and click on it
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("Timeout: Event Classes link not found");
				try { if (sClient.isElementPresent("link=Event Classes")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("link=Event Classes");
			sClient.waitForPageToLoad("30000");
			// Add Service Organizer
			sClient.click("//div[@id='menuslot_Organizer_list']//button");
			sClient.click("//li/a[@id='OrganizerlistaddOrganizer']");
			Thread.sleep(1000);
			sClient.type("//input[@id='new_id']", organizerName);
			Thread.sleep(1000);
			sClient.click("//input[@id='dialog_submit']");
			// Wait for confirmation of organizer creation
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("Timeout: Confirmation of organizer creation not found");
				try { if (sClient.isElementPresent("//div[@class='x-flare-message' and text()='EventClass \"" + organizerName + "\" was created.']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}
			//Wait for list of organizers to show up
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("Timeout: List of organizer not found");
				try { if (sClient.isElementPresent("//tbody[@id='SubClasses']/tr[2]/td[1]")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Open Event Organizer
			sClient.click("//td[@class='tablevalues']/a[text()='" + organizerName + "']");
			sClient.waitForPageToLoad("30000");
			// Click on organizer name on the top of the page to confirm Organizer was opened
			sClient.click("//div[@id='breadCrumbPane']/a[text()='" + organizerName + "']");

			
			testCaseResult = "p";
		}

}

