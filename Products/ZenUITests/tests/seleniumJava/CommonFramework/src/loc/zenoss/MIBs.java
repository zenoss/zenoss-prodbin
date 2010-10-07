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
	 * Create new Mibs
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

	/*
	 * This method assumes that MIBs page is already loaded
	 * Delete new Mibs
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the Mib was successfully deleted or false in other way
	 * @throws Generic Exception
	 */
	public static boolean deleteMIB(DefaultSelenium sClient, String newMIB) throws Exception{
		sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");
		Thread.sleep(1000);
		sClient.click("//span[@class='node-text' and text()='"+newMIB+"']");
		// Click delete option
		Thread.sleep(1000);
		sClient.click("//table[@id='delete-button']");
		// Click on Delete button
		Thread.sleep(1000);
		sClient.click("//*[button='Delete']");
		// Verify Mib is deleted
		Thread.sleep(4000);
		sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");
		Thread.sleep(8000);
		boolean result = false;

		if(sClient.isElementPresent("//span[@class='node-text' and text()='"+newMIB+"']")){
			result = false;
			throw new Exception("The MIB was not deleted");
		}
		else
		{
			result = true;			
		}
		return result;
	}

	/*
	 * This method assumes that MIBs page is already loaded and the MIB is created
	 * Create new OID Mappings
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the Mib was successfully edited or false in other way
	 * @throws Generic Exception
	 */
	public static boolean ediMIBName(DefaultSelenium sClient, String newName, String oldName) throws Exception{
		// Edit MIB name
		// Select a MIB
		sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");
		Thread.sleep(1000);
		sClient.click("//span[@class='node-text' and text()='"+oldName+"']");
		// Click gear menu
		Thread.sleep(1000);
		sClient.click("//table[@id='mibs-configure-menu']/tbody/tr[2]/td[2]/em");
		// Click on Edit Mib
		Thread.sleep(1000);
		sClient.click("edit-mib-action");
		// Change the MIB name
		Thread.sleep(2000);
		sClient.type("newId", newName);
		// Click Submit button
		Thread.sleep(3000);
		sClient.click("//*[button='Submit']");
		sClient.refresh();
		Thread.sleep(20000);
		// Click in the MIB
		sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");
		Thread.sleep(1000);
		sClient.click("//span[@class='node-text' and text()='"+newName+"']");

		Thread.sleep(6000);
		sClient.isElementPresent("//td[text()='"+newName+"']");

		boolean result = true;
		if(sClient.isElementPresent("//span[@class='node-text' and text()='"+newName+"']") ){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The MIB was not edited");
		}
		return result;
	}

	/*
	 * This method assumes that MIBs page is already loaded and the MIB is created
	 * Create new OID Mappings
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the Mib was successfully deleted or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addOIDMappings(DefaultSelenium sClient,String newMIB, String Id, String Oid) throws Exception{
		sClient.doubleClick("//span[@class='node-text' and text()='Mib Classes']");
		sClient.click("//span[@class='node-text' and text()='"+newMIB+"']");
		sClient.selectWindow("null");
		// OID Mappings - Click gear menu
		// Click Add OID Mapping
		Thread.sleep(8000);
		sClient.click("//table[@id='ext-comp-1001']/tbody/tr[2]/td[2]/em");
		Thread.sleep(1000);
		sClient.click("OIDMappingsaddOIDMapping");
		Thread.sleep(2000);
		// Add Id
		sClient.typeKeys("new_id", Id);
		// Add OID
		sClient.typeKeys("oid", Oid);
		Thread.sleep(1000);
		sClient.selectWindow("null");
		sClient.click("//input[@id='dialog_submit']");
		Thread.sleep(5000);
		sClient.isTextPresent("Node "+Id+" was created with oid "+Oid+".");

		boolean result = true;
		if(sClient.isTextPresent(Id)){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The OID Mappings was not created");
		}
		return result;
	}


}

