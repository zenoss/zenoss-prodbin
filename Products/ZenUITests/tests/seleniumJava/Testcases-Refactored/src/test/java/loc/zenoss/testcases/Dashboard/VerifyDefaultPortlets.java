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
package loc.zenoss.testcases.Dashboard;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class VerifyDefaultPortlets {	
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
	public void testDefaultPortlets() throws Exception{		
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
		
		sClient.open("http://test-cent4-64-1.zenoss.loc:8080/zport/dmd?submitted=");		

		Thread.sleep(5000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Device Issues"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Location"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Welcome"));		
		
		/*SeleneseTestCase.assertTrue(sClient.isElementPresent("//div[@id='welcome_handle']/div/div/div/span"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("//div[@id='devissues_handle']/div/div/div/span"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("//div[@id='googlemaps_handle']/div/div/div/span"));		
		*/testCaseResult = "p";
	}
}
