/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
*/
package loc.zenoss.testcases.Reports;

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

public class AddOrganizerViaLeftFrame {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3798;
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
		public void addOrganizerViaLeftFrame() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variable for testing OrganizerName and WinServiceName
			String organizerName = "testReportOrganizer";
			String nestedOrganizerName = "testNestedReportOrganizer";
			// Go to Dashboard > Reports
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Reports");
			sClient.waitForPageToLoad("30000");
			// Add Report Organizer
			sClient.click("//table[@id='add-organizer-button']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[text()='Add Report Organizer...']");
			Thread.sleep(2000);
			sClient.type("//input[@name='name']", organizerName);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//table//button[text()='Submit']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table//button[text()='Submit']");
			// Wait for new Organizer to show up and click on it
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//span[@class='node-text' and text()='" + organizerName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//span[@class='node-text' and text()='" + organizerName + "']");
			// Add nested organizer
			sClient.click("//table[@id='add-organizer-button']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[text()='Add Report Organizer...']");
			Thread.sleep(2000);
			sClient.type("//input[@name='name']", nestedOrganizerName);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//table//button[text()='Submit']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table//button[text()='Submit']");
			// Wait for new nestedOrganizer to show up and click on it
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//span[@class='node-text' and text()='" + nestedOrganizerName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//ul/li/ul/li/div/a/span/span/span[text()='nestedTestOrganizer']");

			
			testCaseResult = "p";
		}

}
