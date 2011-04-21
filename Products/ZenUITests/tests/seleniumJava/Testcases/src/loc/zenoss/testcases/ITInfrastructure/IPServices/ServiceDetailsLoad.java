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

public class ServiceDetailsLoad {

	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;

	private static int testCaseID = 3438;
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
	public void serviceDetailsLoad() throws Exception{
		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		
		// Click Infrastructure
		Thread.sleep(1000);
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		// Click IP Services
		Thread.sleep(3000);
		sClient.click("link=IP Services");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
		// Click on Privileged
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Privileged']");
		Thread.sleep(20000);
		// Search  the "syslog" IPService and select it
		sClient.typeKeys("//*[@name='name']", "SYSLOG");
		Thread.sleep(12000);
		sClient.mouseDown("//table[@class='x-grid3-row-table']//div[text()='syslog']");
		Thread.sleep(5000);
		// Verify that the port is set to 514 
		selenese.verifyEquals("514", sClient.getValue("portTextField"));
		Thread.sleep(1000);
		// Verify that the service keys are syslog, udp_00514 
		selenese.verifyEquals("syslog,udp_00514", sClient.getValue("serviceKeysTextField"));		

		testCaseResult = "p";
	}
}
