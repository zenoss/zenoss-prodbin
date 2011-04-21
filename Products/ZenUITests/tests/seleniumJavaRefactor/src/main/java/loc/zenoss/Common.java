/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
*/
package loc.zenoss;
import com.thoughtworks.selenium.DefaultSelenium;


public class Common {
	
	public static void openUrl(DefaultSelenium sClient, String url)
	{
		sClient.open(url);			
	}
	
	public static void Login(DefaultSelenium sClient, String username, String password) throws Exception
	{
		sClient.open("/");
		sClient.type("username", username);
		sClient.type("__ac_password", password);	
		sClient.click("submitbutton");
		sClient.waitForPageToLoad("40000");
	}
	
	public static void waitForElement(String element, DefaultSelenium sClient) throws Exception
	{
		byte count = 0;
		while(!sClient.isElementPresent(element))
			Thread.sleep(1000);
			count++;
			if(count > 30)
			  throw new Exception("Element not found");

	}
	
	/*
	 * Waits for specified text to appear on the specified target
	 * */
	public static void waitForText(String target, String text, DefaultSelenium sClient) throws Exception
	{
		byte count = 0;
		while(!sClient.getText(target).matches(text))
		{
			Thread.sleep(1000);
			count++;
			if(count > 30)
			  throw new Exception("Text not found");
		}
	}
	
	/*
	 * Insert and model a Single Device on the specified class
	 * @author Alvaro Rivera
	 * @param name Name or IP of the device to add
	 * @param dClass Class where to add the device
	 * @param snmpComm SNMP Community of the device
	 * @param Selenium client connection
	 * @return Boolean true if the device was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addDevice(String name, String dClass, String snmpComm, DefaultSelenium sClient) throws Exception
	{
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
		sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
		Thread.sleep(1500);
		sClient.click("//a[@id='addsingledevice-item']");
		Thread.sleep(7000);
		
		sClient.type("//input[@id='add-device-name']", name);
		sClient.click("//input[@id='add-device_class']");
		Thread.sleep(5000);
		sClient.click("//div//div[31]");
		sClient.getText("//div//div[text() = '"+dClass+"']");
		
		sClient.click("link=More...");
		Thread.sleep(2000);
		sClient.type("ext-comp-1156", snmpComm);
				
		sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]");
		Thread.sleep(5000);
		sClient.click("//*[contains(text(), 'View Job Log')]");
		sClient.waitForPageToLoad("120000");
		
		waitForElement("Job completed at", sClient);
		
		boolean result = true;
		
		if (sClient.isTextPresent("Traceback"))
		{
			result = false;
			throw new Exception("There is tracebacks presents on the Model's process log");
		}
		else if (sClient.isTextPresent("Error"))
		{
			result = false;
			throw new Exception("There is Error presents on the Model's process log");
		}		
		return result;		
	}
}
