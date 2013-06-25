/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Device;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class DeleteOrganizerUserCommand {
	private static int testCaseID = 3981;
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
	public void deleteDeviceUserCommand() throws Exception{
		String deviceClass = "Server";
		String commandID = "NewUserCommand";
		String description = "New command";
		String command = "echo name = ${here/id}";

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("20000");
		Thread.sleep(3000);

		// Click on Device Class
		sClient.click("//span[@class='node-text' and text()='"+deviceClass+"']");
		//Click on details view
		sClient.click("//*[button='Details']");

		// Click on Administration
		Thread.sleep(5000);
		sClient.click("//ul[@id='ext-gen253']/div/li[6]/div/a/span");
		Thread.sleep(15000);
		// Click on gear menu on Define Commands
		sClient.click("//table[@id='ext-comp-1001']/tbody/tr[2]/td[2]/em");
		// Click on Add User Command...
		Thread.sleep(1000);
		sClient.click("UserCommandlistaddUserCommand");
		// Enter Command ID
		Thread.sleep(1000);
		sClient.type("new_id", commandID);
		// Click Ok button
		Thread.sleep(1000);
		sClient.click("//input[@id='dialog_submit']");
		Thread.sleep(5000);
		selenese.verifyTrue(sClient.isTextPresent("User command "+commandID+" has been created."));
		// Enter a Description
		sClient.type("description:text", description);
		// Enter a Command
		sClient.type("command:text", command);
		// Type admin password
		sClient.type("password", ZenossConstants.adminPassword);
		sClient.selectWindow("null");
		// Click on Save button
		Thread.sleep(2000);
		sClient.click("//input[@value=' Save ']");
		Thread.sleep(6000);
		selenese.verifyTrue(sClient.isElementPresent("//a[text()='"+commandID+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//td[text()='"+description+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//td[text()='"+command+"']"));

		Thread.sleep(2000);
		// Delete Organizer User Command
		// Select the command created
		sClient.click("//input[@name='ids:list' and @value='"+commandID+"']");
		// Click on gear menu
		sClient.click("//table[@id='ext-comp-1001']/tbody/tr[2]/td[2]/em");
		// Click on Delete Commands
		Thread.sleep(1000);
		sClient.click("UserCommandlistdeleteUserCommands");
		// Click on OK button
		Thread.sleep(1000);
		sClient.click("//input[@value='OK']");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("User commands "+commandID+" have been deleted."));
		selenese.verifyFalse(sClient.isElementPresent("//a[text()='"+commandID+"']"));
		selenese.verifyFalse(sClient.isElementPresent("//td[text()='"+description+"']"));
		selenese.verifyFalse(sClient.isElementPresent("//td[text()='"+command+"']"));

		testCaseResult = "p";
	}
}
