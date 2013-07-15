/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Devices.AddDevices;


import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;
import loc.zenoss.Common;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class DiscoverWindows2003onWindowsClass {

private static DefaultSelenium sClient = null;
	private static int testCaseID = 2045;
	private static String testCaseResult = "f"; //Fail by default
		
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, "http://test-cent4-64-2.zenoss.loc:8080")  {// ZenossConstants.testedMachine)  {
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
	public void AddWindows2003Devices() throws Exception {
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
				
		sClient.open("/");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		
		boolean status = Common.addDevice("test-win2003-1d.zenoss.loc", "/Server/Windows", "public", sClient); 
		
		if (!status)
			SeleneseTestCase.fail("Problems when add Device");
		
		/*sClient.click("link=IT Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
		sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
		Thread.sleep(1500);
		sClient.click("//a[@id='addsingledevice-item']");
		Thread.sleep(7000);
		
		sClient.type("//input[@id='add-device-name']", "test-win2003-1d.zenoss.loc");
		sClient.click("//input[@id='add-device_class']");
		Thread.sleep(5000);
		sClient.click("//div//div[31]");
		System.out.print(sClient.getText("//div//div[31]"));
		sClient.click("link=More...");
		Thread.sleep(2000);
		sClient.type("ext-comp-1146", "public");
		
		sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]");
		Thread.sleep(5000);
		sClient.click("//*[contains(text(), 'View Job Log')]");
		sClient.waitForPageToLoad("120000");
		
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Traceback"));
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Error"));
			*/
		
		
		
		
		/*
		sClient.open("/zport/dmd/itinfrastructure");
		Thread.sleep(5000);
		sClient.click("link=test-win2003-1d.zenoss.loc");
		sClient.waitForPageToLoad("120000");
		Thread.sleep(10000);
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=/Server/Windows"));
		
		sClient.click("//ul[@id='ext-gen182']/div/li[7]/div/a/span");
		Thread.sleep(10000);
		
		sClient.type("zWinUser", "Administrator");
		sClient.type("zWinPassword", "ZenossQA1");
		sClient.click("saveZenProperties:method");
		sClient.waitForPageToLoad("30000");
		
		/* Remodel device option is still not implemented and is needed in order to execute the following steps
		 * 
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Traceback"));
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Error"));
		 */
		
		testCaseResult = "p";
	}
}
