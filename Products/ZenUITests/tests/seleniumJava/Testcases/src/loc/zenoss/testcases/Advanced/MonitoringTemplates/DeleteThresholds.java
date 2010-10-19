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
package loc.zenoss.testcases.Advanced.MonitoringTemplates;

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

public class DeleteThresholds {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3732;
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
		public void deleteThresholds() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set variable for Testing Template and Threshold name
			String templateName = "a_testTemplate";
			String thresholdName = "testThreshold";
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			sClient.click("//button[text()='Template']");
			Thread.sleep(4000);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']/div/div/ul/div/li[1]/div/a/span")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Add new template
			sClient.click("//table[@id='footer_add_button']//button[@class=' x-btn-text add']");
			sClient.type("//input[@name='id']", templateName);
			// Click Template Path list, wait for list to populate and select "Linux in Devices/Server"
			sClient.click("//html/body/div[@id='addNewTemplateDialog']//form/div[2]/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[text()='Linux in Devices/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(2000);
			sClient.click("//div[text()='Linux in Devices/Server']");
			Thread.sleep(2000);
			sClient.click("//button[text()='Submit']");
			// Wait for templates list to refresh and show the new template
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//span[text()='" + templateName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//span[text()='/Server/Linux']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Click the Add Threshold button
			sClient.click("//table[@id='thresholdAddButton']//button");
			// Click the type list, wait for list to populate and select "MinMaxThreshold" type
			sClient.click("//html/body/div[@id='addThresholdDialog']//form/div/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[text()='MinMaxThreshold']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='MinMaxThreshold']");
			Thread.sleep(1000);
			// Type the desired threshold name and click on Add button
			sClient.type("//input[@name='thresholdIdField']", thresholdName);
			Thread.sleep(1000);
			sClient.click("//button[text()='Add']");
			// Wait for the new threshold to show up and click on it
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.mouseDown("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			sClient.mouseUp("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			// Click the button to Edit the new threshold
			sClient.click("//table[@id='thresholdDeleteButton']//button");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//td/em/button[text()='Remove']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//td/em/button[text()='Remove']");
			Thread.sleep(4000);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (!sClient.isElementPresent("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}
			// END
		
			Thread.sleep(1000);
			testCaseResult = "p";
		}

}

