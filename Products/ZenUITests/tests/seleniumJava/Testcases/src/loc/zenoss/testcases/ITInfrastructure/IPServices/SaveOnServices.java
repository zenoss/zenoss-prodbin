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
package loc.zenoss.testcases.ITInfrastructure.IPServices;

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

public class SaveOnServices {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;

	private static int testCaseID =  3222;
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
	public void saveOnServices() throws Exception{
		String description1 = "Zenoss IP services";
		String description2 = "Privileged Zenoss IP services";
		String description3 = "Registered Zenoss IP services";
		
		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		sClient.click("link=IP Services");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		// Edit IPservices description
		Thread.sleep(5000);
		sClient.click("//span[normalize-space(@class)='node-text' and text()='IpService']");
		sClient.typeKeys("descriptionTextField", description1);
		Thread.sleep(8000);
		// Save the new changes
		sClient.click("//*[button='Save']");
		Thread.sleep(5000);
		// Click on Privileged
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Privileged']");
		Thread.sleep(8000);
		sClient.typeKeys("descriptionTextField", description2);
		Thread.sleep(6000);
		sClient.click("//*[button='Save']");
		Thread.sleep(5000);
		// Click on Registered
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Registered']");
		Thread.sleep(8000);
		sClient.typeKeys("descriptionTextField", description3);
		Thread.sleep(5000);
		sClient.click("//*[button='Save']");
		Thread.sleep(12000);
		// Verify your changes on IpService
		sClient.click("//span[normalize-space(@class)='node-text' and text()='IpService']");
		Thread.sleep(10000);
		selenese.verifyEquals(description1, sClient.getValue("descriptionTextField"));
		Thread.sleep(10000);
		// Verify your changes on Privileged
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Privileged']");
		Thread.sleep(10000);
		selenese.verifyEquals(description2, sClient.getValue("descriptionTextField"));
		Thread.sleep(8000);
		// Verify your changes on Registered
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Registered']");
		Thread.sleep(10000);
		selenese.verifyEquals(description3, sClient.getValue("descriptionTextField"));

	}
}
