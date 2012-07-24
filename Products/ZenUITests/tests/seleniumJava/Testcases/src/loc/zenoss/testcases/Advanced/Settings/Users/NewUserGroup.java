/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Advanced.Settings.Users;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.Users;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class NewUserGroup {

	private static int testCaseID = 1805;
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
	public void managerUser() throws Exception{
		String group = "GroupZenoss1";

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		sClient.open("/zport/dmd/?submitted=true");
		// Click on Advanced
		sClient.click("link=Advanced");
		sClient.waitForPageToLoad("30000");
		// Click Users
		sClient.click("link=Users");
		sClient.waitForPageToLoad("30000");

		//Add new user group
		Users.newUserGroup(sClient, group);
		Thread.sleep(1000);
		selenese.verifyTrue(sClient.isElementPresent("//a[text()='"+group+"']"));

		testCaseResult = "p";

	}
}
