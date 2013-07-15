/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Advanced.Settings.Zenpacks;

import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;


public class CheckCoreZenpackList {
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
	 * Verifies the complete list of installed zenpack on a full rpm core installation
	 * @throws Exception
	 */
	@Test
	public void testVerifyCoreZenpackList() throws Exception{		
		
		testCaseID = 3758;
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		*/
		sClient.open("/");
		Thread.sleep(2000);
		sClient.open("/zport/dmd/editSettings");
		Thread.sleep(8000);
		sClient.click("link=ZenPacks");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.ApacheMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.DellMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.DigMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.DnsMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.FtpMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.HPMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.HttpMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.IRCDMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.JabberMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.LDAPMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.LinuxMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.MySqlMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.NNTPMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.NtpMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.RPCMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.XenMonitor"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.ZenJMX"));
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=ZenPacks.zenoss.ZenossVirtualHostMonitor"));
		
		testCaseResult = "p";
	}
}
