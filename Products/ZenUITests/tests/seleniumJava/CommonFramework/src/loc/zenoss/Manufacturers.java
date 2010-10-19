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

public class Manufacturers {

	/*
	 * This method assumes that manufacturers page is already loaded
	 * Create new manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the manufacturers was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean createManufacturers(DefaultSelenium sClient, String manufacturer ) throws Exception{

		// Click on gear menu
		Thread.sleep(4000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// click Add Manufacturer
		Thread.sleep(2000);
		sClient.click("//a[text()='Add Manufacturer...']");
		Thread.sleep(2000);
		sClient.type("new_id", manufacturer);
		sClient.click("//input[@id='dialog_submit']");
		Thread.sleep(8000);
		// Click on show All
		sClient.click("showAll");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);

		//Verify if the manufacturer was created.
		boolean result = true;
		if(sClient.isElementPresent("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new Manufacturer was not created");
		}
		return result;
	}

	/*
	 * This method assumes that manufacturers page is already loaded
	 * and the manufacturer was created.
	 * Delete manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the manufacturers was successfully deleted or false in other way
	 * @throws Generic Exception
	 */
	public static boolean deleteManufacturers1(DefaultSelenium sClient, String manufacturer ) throws Exception{
		// Delete Manufacturer
		// Click on the manufacturer
		sClient.click("//input[@type='checkbox' and @value='"+manufacturer+"']");
		// Click gear menu
		Thread.sleep(3000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// Click Delete Manufacturers
		sClient.click("ManufacturerlistremoveManufacturers");
		Thread.sleep(2000);
		sClient.click("//input[@value='OK']");
		// Click on show All
		sClient.click("showAll");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);

		boolean result = false;

		if(sClient.isElementPresent("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']")){
			result = false;
			throw new Exception("The Manufacturer was not deleted");
		}
		else
		{
			result = true;			
		}
		return result;		
	}
	
}
