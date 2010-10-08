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
package loc.zenoss.testcases.Device;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.Device;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddDeviceUserCommand {
	private static int testCaseID = 3963;
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
	public void addDeviceUserCommand() throws Exception{
		String device = "test-hpux.zenoss.loc";
		String deviceClass = "/Server/SSH/HP-UX";
		String commandID = "NewUserCommand";
		String description = "New command";
		String command = "echo name = ${here/id}";


		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);
		//Add device
		Device addDevice = new Device(""+device+"",sClient);
		addDevice.add(""+deviceClass+"");
		Thread.sleep(10000);

		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		// Click on the device
		sClient.click("link="+device+"");
		sClient.waitForPageToLoad("30000");
		// Click on Administration
		Thread.sleep(5000);
		sClient.click("//ul[@id='ext-gen243']/div/li[7]/div/a/span");
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

		testCaseResult = "p";

	}
}
