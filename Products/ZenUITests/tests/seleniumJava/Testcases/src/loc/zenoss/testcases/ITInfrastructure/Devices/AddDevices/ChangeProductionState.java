/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
*/
package loc.zenoss.testcases.ITInfrastructure.Devices.AddDevices;


import loc.zenoss.Common;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class ChangeProductionState {

	private static DefaultSelenium sClient = null;

	private static int testCaseID;
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
	public void changeProductionState() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		/*sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Devices");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("ext-gen61");
		sClient.click("x-menu-el-addmultipledevices-item");
		sClient.waitForPopUp("multi_add", "30000");
		sClient.selectWindow("name=multi_add");
		sClient.click("autoradio");
		sClient.type("ext-comp-1003", "10.175.211.0/24");
		sClient.click("ext-gen84");
		sClient.selectWindow(null);
		Thread.sleep(12000);*/
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Devices");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("//div[@id='ext-gen74']/div/table/tbody/tr/td[1]/div/../..");
		sClient.click("ext-gen65");
		sClient.click("ext-gen155");
		sClient.click("ext-gen193");
		sClient.click("//div[@id='ext-gen203']/div[4]");
		sClient.click("ext-gen186");
		

		
	}
	/**
	 * Create a Backup whit DefaultSettings Testcase 1822
	 * @throws Exception
	 */
	

}
