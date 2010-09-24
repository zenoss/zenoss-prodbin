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
package loc.zenoss.testcases.ITInfrastructure.Devices;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddDeviceWindows {
	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
		
	
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)   {
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
		 selenese = new SeleneseTestCase();
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	
	@Test
	public void addSingleDevice(String Devicename) throws Exception
	{
		//Login into System
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		//Go to INFRASTRUCTURE
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		//Click on Add Device Button
		sClient.click("ext-gen77");
		//Click on Single Device
		sClient.click("ext-gen247");
		//Enter Devicename or IP
		sClient.type("add-device-name", Devicename);
		//Click on DeviceClass Combobox
		sClient.click("ext-gen292");
		sClient.click("//div[@id='ext-gen356']/div[57]");
		//Click on Submitt
		sClient.click("ext-gen278");
		//Wait until we get the job notification
		Thread.sleep(5000);
		sClient.waitForPageToLoad("30000");
		//Verify notification message
		selenese.verifyTrue(sClient.isTextPresent("View Job Log"));
		//Verify Device was properly added
		sClient.click("link=Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		selenese.verifyTrue(sClient.isTextPresent(Devicename));		
	}

}
