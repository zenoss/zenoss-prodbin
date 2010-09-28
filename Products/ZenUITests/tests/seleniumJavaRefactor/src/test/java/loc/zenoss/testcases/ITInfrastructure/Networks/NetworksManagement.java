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
package loc.zenoss.testcases.ITInfrastructure.Networks;

import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;


public class NetworksManagement {
private static DefaultSelenium sClient = null;
	
	private static int testCaseID;
	private static String testCaseResult; //Fail by default
		
	
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
		
	}

	@Before
	public void setUp() throws Exception {
		testCaseResult = "f";
	}

	@After
	public void tearDown() throws Exception {
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}
	
	
	/**
	 * Add a network Testcase 3758
	 * @throws Exception
	 */
	@Test
	public void testAddNetwork() throws Exception{		
		
		testCaseID = 3758;
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		*/
		sClient.open("/");
		Thread.sleep(2000);
		sClient.open("/zport/dmd/networks");
		Thread.sleep(6000);
		sClient.click("link=Networks");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(6000);
		sClient.click("ext-gen26");
		Thread.sleep(3000);
		sClient.type("addNetworkTextfield", "192.168.1.0/24");
		sClient.click("//table[@id='ext-comp-1052']/tbody/tr[2]/td[2]");
		Thread.sleep(5000);
		SeleneseTestCase.assertEquals("192.168.1.0/24", sClient.getText("//ul[@id='ext-gen119']/li/div/a/span"));
		testCaseResult = "p";
	}
	
	@Test
	public void testRemoveNetwork() throws Exception
	{
		testCaseID = 3760;
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		*/
		sClient.open("/");
		Thread.sleep(2000);
		sClient.open("/zport/dmd/networks");
		Thread.sleep(6000);
		sClient.click("link=Networks");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(6000);
		SeleneseTestCase.assertEquals("192.168.1.0/24", sClient.getText("//ul[@id='ext-gen119']/li/div/a/span"));
		
		sClient.click("//ul[@id='ext-gen119']/li/div/a/span");		
		sClient.click("ext-gen28");
		Thread.sleep(3000);
		sClient.click("//table[@id='ext-comp-1055']/tbody/tr[2]/td[2]");
		Thread.sleep(3000);
		SeleneseTestCase.assertFalse(sClient.isElementPresent("//ul[@id='ext-gen119']/li/div/a/span"));
		SeleneseTestCase.assertFalse(sClient.isTextPresent("192.168.1.0/24"));
		testCaseResult = "p";
	}
}
