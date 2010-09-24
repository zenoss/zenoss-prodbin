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
package loc.zenoss.testcases.Advanced;

import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class NavigationAdvanced {

private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 1790;
	private static String testCaseResult = "f"; //Fail by default

	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)  {
        	public void open(String url) {
        		commandProcessor.doCommand("open", new String[] {url,"true"});
        	}
        };
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
	public void naviAdvanced() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
		sClient.open("/zport/dmd/Dashboard");
		 sClient.waitForPageToLoad("30000");
		sClient.click("link=Advanced");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Monitoring Templates"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Collectors"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("MIBs"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Settings"));
		sClient.click("link=Monitoring Templates");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Monitoring Templates"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Data Sources"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Thresholds"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Graph Definitions"));
		sClient.click("link=Collectors");
		 sClient.waitForPageToLoad("30000");
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("localhost"));
		sClient.click("link=MIBs"); 
		 sClient.waitForPageToLoad("30000");
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Sub-Folders"));
		 sClient.click("link=Modifications");
		 sClient.waitForPageToLoad("30000");
	    sClient.click("link=Settings");
		 sClient.waitForPageToLoad("30000");
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Settings"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Commands"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Users"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("ZenPacks"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Jobs"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Menus"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Portlets"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Daemons"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Versions"));
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Backups"));

	}

}
