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
package loc.zenoss.testcases.ITInfrastructure.OSProcesses;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class AddOSProcess {

	private static int testCaseID = 2230;
	private static String testCaseResult = "f"; //Fail by default
	
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
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
		public void addOSProcess() throws Exception{
			Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/Dashboard");
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Add new Device
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addsingledevice-item");
			Thread.sleep(1000);
			sClient.type("add-device-name", "test-sql2005-1d.zenoss.loc");
			Thread.sleep(1000);
			sClient.typeKeys("add-device_class", "/Server/Windows/");
			Thread.sleep(2000);
			sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
			Thread.sleep(6000);
			sClient.click("link=View Job Log");
			// Job verification
			Thread.sleep(40000);
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(6000);
			// Click on the device added
			sClient.click("link=test-sql2005-1d.zenoss.loc");
			sClient.waitForPageToLoad("30000");
			// Add new OS Process
			Thread.sleep(8000);
			sClient.click("//table[@id='component-add-menu']/tbody/tr[2]/td[2]/em");
			Thread.sleep(3000);
			sClient.click("addosprocess");
			Thread.sleep(2000);
			sClient.typeKeys("newClassName", "httpd");
			Thread.sleep(1000);
			selenese.verifyTrue(sClient.isTextPresent("httpd"));
			Thread.sleep(1000);
			sClient.click("//*[button='Submit']");
			Thread.sleep(3000);
			selenese.verifyTrue(sClient.isTextPresent("Add OSProcess finished successfully"));
			// Select OS Processes component
			Thread.sleep(2000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='OS Processes']");
			// Verify the http process 
			Thread.sleep(5000);
			selenese.verifyTrue(sClient.isTextPresent("httpd"));
			selenese.verifyEquals("httpd", sClient.getText("link=httpd"));
			// Click on httpd Process
			sClient.click("link=httpd");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			selenese.verifyEquals("httpd", sClient.getValue("nameTextField"));
			selenese.verifyEquals("Apache httpd web server process",sClient.getValue("ext-comp-1084"));
			// Verify that the device is displayed on the httpd process
			Thread.sleep(1000);
			selenese.verifyEquals("test-sql2005-1d.zenoss.loc", sClient.getText("link=test-sql2005-1d.zenoss.loc"));
			
			testCaseResult = "p";
		}
}
