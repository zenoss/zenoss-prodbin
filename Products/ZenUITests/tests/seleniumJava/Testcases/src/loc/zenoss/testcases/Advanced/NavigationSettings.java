/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Advanced;


//import loc.zenoss.Common;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
//import com.thoughtworks.selenium.SeleneseTestCase;

public class NavigationSettings {
	
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
	public void navigationSettings() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd/Dashboard");
		 sClient.waitForPageToLoad("30000");
		sClient.click("link=Advanced");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
	    sClient.click("link=Settings");
	     sClient.waitForPageToLoad("30000");
	     Thread.sleep(3000);
		 sClient.click("link=Commands");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Backups");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Users");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 sClient.click("link=ZenPacks");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Portlets");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Jobs");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Menus");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Daemons");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Versions");
		 sClient.waitForPageToLoad("30000");
		 
	}

}
