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

public class AddZenpackButton_Report {
	private static int testCaseID = 3590;
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
	public void addZenpackButton() throws Exception{
		String zenpack = "ZenPacks.zenoss.A1Zenpack";
		String report = "aNewReportOrganizer";
		String path = "/Reports/aNewReportOrganizer";

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

		// Go to Report page
		sClient.click("link=Reports");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(4000);
		// Create new Organizer
		// Click gear menu
		sClient.click("//table[@id='add-organizer-button']/tbody/tr[2]/td[2]/em");
		// Click on Add Report Organizer
		Thread.sleep(1000);
		sClient.click("//span[@class='x-menu-item-text' and text()='Add Report Organizer...']");
		// Type Organizer name
		sClient.typeKeys("//input[@name='name']", report);
		// click on Submit button
		Thread.sleep(1000);
		sClient.click("//*[button='Submit']");
		// Select the Report created
		Thread.sleep(5000);
		sClient.click("//span[@class='node-text' and text()='"+report+"']");
		// Click on Add to ZenPack button
		Thread.sleep(1000);
		sClient.click("add-to-zenpack-button");
		// Select the zenpack created
		Thread.sleep(2000);
		sClient.click("//div[@id='addzenpackform']//img");
		Thread.sleep(4000);
		sClient.click("//div[normalize-space(@class) = 'x-combo-list-item' and text()='"+zenpack+"']");

		Thread.sleep(1000);
		sClient.click("//*[button='Submit']");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("The item was added to the zenpack, "+zenpack+""));
		// Click Advanced
		sClient.click("link=Advanced");
		// Click on ZenPacks
		Thread.sleep(4000);
		sClient.click("link=ZenPacks");
		sClient.waitForPageToLoad("30000");
		// Click on the zenpack created
		sClient.click("link="+zenpack+"");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("//tbody[@id='ZenPackProvides']/tr/td/a[text()='"+path+"']"));
		
		testCaseResult = "p";
	}
}
