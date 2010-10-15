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
package loc.zenoss.testcases.Reports;

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

public class ReportPage {
	private static int testCaseID = 3795;
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
	public void reportPage() throws Exception{

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		// Click on Reports page
		sClient.click("link=Reports");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(6000);
		// Verify Report Classes
		selenese.verifyTrue(sClient.isElementPresent("//span[@class='node-text' and text()='Report Classes']"));
		Thread.sleep(1000);
		sClient.click("//table[@id='add-organizer-button']/tbody/tr[2]/td[2]/em");
		Thread.sleep(1000);
		selenese.verifyTrue(sClient.isElementPresent("//span[@class='x-menu-item-text' and text()='Add Report Organizer...']"));
		selenese.verifyTrue(sClient.isElementPresent("//span[@class='x-menu-item-text' and text()='Add Custom Device Report...']"));
		selenese.verifyTrue(sClient.isElementPresent("//span[@class='x-menu-item-text' and text()='Add Graph Report...']"));
		selenese.verifyTrue(sClient.isElementPresent("//span[@class='x-menu-item-text' and text()='Add Multi-Graph Report...']"));
		selenese.verifyTrue(sClient.isElementPresent("//button[@class=' x-btn-text delete']"));
		selenese.verifyTrue(sClient.isElementPresent("//button[@class=' x-btn-text set']"));
		selenese.verifyTrue(sClient.isElementPresent("//button[@class=' x-btn-text adddevice']"));

		testCaseResult = "p";
	}
}
