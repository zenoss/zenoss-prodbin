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
package loc.zenoss.testcases.Device;

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

public class ProductState {

	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3769;
	private static String testCaseResult = "f"; //Fail by default
		
	@BeforeClass
	 public static void setUpBeforeClass() throws Exception {
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
		public void removeDevice() throws Exception{
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/?submitted=true");
			Thread.sleep(3000);
			// Click Infrastructure
			sClient.click("link=Infrastructure");
			// Add Multiple Devices
			Thread.sleep(6000);
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addmultipledevices-item");
			sClient.waitForPopUp("multi_add", "30000");
			// Click on Auto discover
			sClient.selectWindow("name=multi_add");
			sClient.click("autoradio");
			// Type an IP range
			Thread.sleep(1000);
			sClient.type("ext-comp-1003", "10.175.211.3-5");
			// Click on Discover button
			sClient.click("//*[button='Discover']");
			Thread.sleep(55000);
			// Refresh Device page
			sClient.selectWindow("null");
			sClient.refresh();
			sClient.waitForPageToLoad("30000");
			sClient.selectWindow("null");
			sClient.click("link=Devices");
			sClient.waitForPageToLoad("30000");
			// Click Discovered Class
			Thread.sleep(2000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Discovered']");
			// Select All the devices
			Thread.sleep(1000);
			sClient.click("//*[button='Select']");
			sClient.click("//span[@class='x-menu-item-text' and text()='All']");
			// Click on Actions menu
			sClient.click("//table[@id='actions-menu']/tbody/tr[2]/td[2]/em");
			// Click on Set Production State
			sClient.click("//span[@class='x-menu-item-text' and text()='Set Production State...']");
			// Select Maintenance State
			Thread.sleep(2000);
			sClient.click("//div[@id='x-form-el-prodstate']//img");
			Thread.sleep(2000);
			sClient.click("//div[normalize-space(@class) = 'x-combo-list-item' and text()= 'Maintenance']");
			selenese.verifyEquals("Maintenance", sClient.getValue("prodstate"));
			// Click Ok button
			sClient.click("//*[button='OK']");
			// Select in Production State the state selected
			Thread.sleep(1000);
			sClient.click("//table[@id='productionState']/tbody/tr[2]/td[2]/em");
			// Select Maintenance state
			sClient.click("//span[@class='x-menu-item-text' and text()='Maintenance']");
			// Verify that production state set to Maintenance 
			Thread.sleep(3000);
			selenese.verifyTrue(sClient.isTextPresent("Maintenance"));
			selenese.verifyFalse(sClient.isElementPresent("Production"));

			
			testCaseResult = "p";
		}
	
}
