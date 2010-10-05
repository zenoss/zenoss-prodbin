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

public class MIBs {

		/*
		 * This method assumes that MIBs page is already loaded
		 * Ceate new Mibs
		 * @author Catalina Rojas 
		 * @param sClient Selenium client connection
		 * @return Boolean true if the Mib was successfully added or false in other way
		 * @throws Generic Exception
		 */
		public static boolean addMIB(DefaultSelenium sClient, String newMIB) throws Exception{
			sClient.click("//table[@id='add-organizer-button']/tbody/tr[2]/td[2]/em");
			Thread.sleep(1000);
			sClient.click("//span[@class='x-menu-item-text' and text()='Add blank MIB...']");
			Thread.sleep(1000);
			sClient.typeKeys("name", newMIB);
			Thread.sleep(2000);
			sClient.click("//*[button='Submit']");
			Thread.sleep(3000);
			sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");			
			Thread.sleep(10000);
			
			boolean result = true;
			if(sClient.isElementPresent("//span[@class='node-text' and text()='"+newMIB+"']") ){
				result = true;
			}
			else
			{
				result = false;
				throw new Exception("The new MIB was not created");
			}
			return result;

		}
	
}
