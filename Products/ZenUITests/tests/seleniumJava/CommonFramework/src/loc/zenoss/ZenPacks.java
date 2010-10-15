/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
 */
package loc.zenoss;
import com.thoughtworks.selenium.DefaultSelenium;

public class ZenPacks {

	/*
	 * This method assumes that Zenpacks page is already loaded
	 * Create new Zenpack
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the Zenpack was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean createZenpack(DefaultSelenium sClient, String zenpack) throws Exception{
		// Click on gear menu
		Thread.sleep(1000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// Click on Create a ZenPack
		sClient.click("ZenPacklistaddZenPack");
		Thread.sleep(1000);
		// Enter new Zenpack name
		Thread.sleep(2000);
		sClient.type("new_id", zenpack);
		// Click Ok button
		Thread.sleep(2000);
		sClient.click("//input[@value='OK']");
		Thread.sleep(12000);
		sClient.click("link=ZenPacks");
		sClient.refresh();
		sClient.waitForPageToLoad("30000");
		Thread.sleep(10000);
		// Verify Zenpack

		boolean result = true;
		if(sClient.isElementPresent("//tbody[@id='LoadedZenPacks']/tr/td/a[text()='"+zenpack+"']")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new ZenPack was not created");
		}
		return result;
	}

}
