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
package loc.zenoss.testcases.ITInfrastructure.WindowsServices;

import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.Services;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class AddingIPServicesOrganizer {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 2215;
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
		public void addingIPServicesOrganizer() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variable for testing OrganizerName and WinServiceName
			String orgName = "ABCD";
			String servName = "DEFG";
			

			// Go to Dashboard > Infrastructure
			
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			// Wait for IP Services link and click on it
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("link=IP Services")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("link=IP Services");
			sClient.waitForPageToLoad("30000");

			// Add Service Organizer
			sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[text()='Add Service Organizer']");
			Thread.sleep(2000);
			sClient.type("//input[@name='id']", orgName);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//table[@class='x-btn   x-btn-noicon ']//button[text()='Submit']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//button[text()='Submit']");
			// Refresh IP Services page to load
			sClient.click("link=IP Services");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//ul[@class='x-tree-node-ct']/li")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			//Services.addServiceOrganizer(orgName, sClient);
			
			// Click on the Service Organizer
			sClient.click("//span[@class='node-text' and text()='" + orgName + "']");
			// Add a Service
			sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[text()='Add Service']");
			Thread.sleep(2000);
			sClient.type("//input[@name='id']", servName);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//table[@class='x-btn   x-btn-noicon ']//button[text()='Submit']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//button[text()='Submit']");
			// Refresh IP Services page to load
			sClient.click("link=IP Services");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//ul[@class='x-tree-node-ct']/li")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@class='x-grid3-body']/div")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Click on the Service Organizer
			sClient.click("//span[@class='node-text' and text()='" + orgName + "']");
			// Wait for Services list to load and open the service
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + servName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.mouseDownAt("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + servName + "']", "");
			sClient.mouseUp("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + servName + "']");
			
			// Clicks to verify expected UI is present: Name, Description, Service Keys, Enable Monitoring?, Failure Event Severity
			sClient.click("//input[@id='nameTextField']");
			sClient.click("//input[@id='descriptionTextField']");
			sClient.click("//input[@id='portTextField']");
			sClient.click("//input[@id='sendStringTextField']");
			sClient.click("//input[@id='expectRegexTextField']");
			sClient.click("//textarea[@id='serviceKeysTextField']");
			sClient.click("//label[@class='x-form-cb-label' and @for='ext-comp-1100' and text()='Set Local Value:']");
			sClient.click("//input[@id='ext-comp-1103']");
			sClient.click("//label[@class='x-form-cb-label' and text()='Inherit Value \"No\" from Services']");
			sClient.click("//label[@class='x-form-cb-label' and @for='ext-comp-1108' and text()='Set Local Value:']");
			sClient.click("//input[@id='ext-comp-1111']");
			sClient.click("//label[@class='x-form-cb-label' and text()='Inherit Value \"Critical\" from Services']");

			testCaseResult = "p";
		}

}
