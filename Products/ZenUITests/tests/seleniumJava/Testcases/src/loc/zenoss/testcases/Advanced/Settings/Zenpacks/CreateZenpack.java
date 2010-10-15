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
package loc.zenoss.testcases.Advanced.Settings.Zenpacks;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.ZenPacks;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class CreateZenpack {
	private static int testCaseID = 3953;
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
	public void createZenpack() throws Exception{
		String zenpack = "ZenPacks.zenoss.CreateZenPack";

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("20000");
		Thread.sleep(3000);

		// Click on Advaced
		Thread.sleep(2000);
		sClient.click("link=Advanced");
		// Click on ZenPacks
		Thread.sleep(5000);
		sClient.click("link=ZenPacks");
		sClient.waitForPageToLoad("30000");

		//Create new Zenpack
		ZenPacks.createZenpack(sClient, zenpack);
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='LoadedZenPacks']/tr/td/a[text()='"+zenpack+"']"));

		testCaseResult = "p";
	}
}
