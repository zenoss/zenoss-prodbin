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
package loc.zenoss.testcases.Advanced.Settings.Users;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.Users;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;


public class DeleteUserWithGroup {

	private static int testCaseID = 1811;
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
	public void deleteUserWithGroup() throws Exception{
		//Deleted user should also be deleted from group lists
		String user = "testing005";
		String group = "GroupZenoss5";

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		sClient.open("/zport/dmd/?submitted=true");
		// Click on Advanced page
		sClient.click("link=Advanced");
		sClient.waitForPageToLoad("30000");

		// Click Users page
		sClient.click("link=Users");
		sClient.waitForPageToLoad("30000");

		//Add new user
		Users.addNewUser(sClient, user, "testing005@test.zenoss.com");

		//Create new Group
		Users.newUserGroup(sClient, group);
		Thread.sleep(3000);
		selenese.verifyTrue(sClient.isElementPresent("//a[text()='"+group+"']"));

		Thread.sleep(3000);
		//Add user to a group
		Users.UserToGroup(sClient, user, group);

		//Delete the user created
		Users.deleteUser(sClient, user);

		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Groups']//td[text()='"+group+"']"));
		Thread.sleep(1000);
		//	selenese.verifyFalse(sClient.isElementPresent("testGroup1"));

		testCaseResult = "p";
	}
}
