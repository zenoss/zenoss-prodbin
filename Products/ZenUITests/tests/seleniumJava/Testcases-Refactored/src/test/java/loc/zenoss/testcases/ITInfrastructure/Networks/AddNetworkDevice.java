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
package loc.zenoss.testcases.ITInfrastructure.Networks;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddNetworkDevice {
	private static DefaultSelenium sClient = null;
	private String devicename;
		
	
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
		 new SeleneseTestCase();
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	
	@Test
	public void addSingleDevice() throws Exception
	{
		//Login into System
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		//Go to INFRASTRUCTURE
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		//Enter Network Device name with SNMP
		sClient.type("add-device-name", devicename);
		// Click Device Class select Network/Switch
		sClient.click("ext-gen298");
		sClient.click("//div[@id='ext-gen362']/div[29]");
		//Click Submmit
		sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]");			
	}
}