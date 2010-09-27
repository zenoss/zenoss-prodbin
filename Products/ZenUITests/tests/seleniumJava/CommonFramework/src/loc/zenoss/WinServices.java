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
import com.thoughtworks.selenium.SeleneseTestCase;


public class WinServices {
	
	/*
	 * This method assumes that Windows Services page is already loaded
	 * and inserts a new Service Organizer at Windows Services view
	 * @author Jose Rodriguez
	 * @param organizerName or name of the organizer to add
	 * @param sClient Selenium client connection
	 * @return Boolean true if the organizer was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addWinServiceOrganizer(String organizerName, DefaultSelenium sClient) throws Exception
	{
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		sClient.click("//span[text()='Add Service Organizer']");
		Thread.sleep(2000);
		sClient.type("//input[@name='id']", organizerName);
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//table[@class='x-btn   x-btn-noicon ']//button[text()='Submit']")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		sClient.click("//button[text()='Submit']");
		// Refresh page and wait for Organizers list to load
		sClient.click("link=Windows Services");
		sClient.waitForPageToLoad("30000");
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//ul[@class='x-tree-node-ct']/li")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		boolean result = true;
		
		if (!sClient.isElementPresent("//span[@class='node-text' and text()='" + organizerName + "']"))
		{
			result = false;
			throw new Exception("The new service organizer is not found");
		}
		
		return result;		
	}
	
	/*
	 * This method assumes that Windows Services page is already loaded
	 * and inserts a new Service at the specified service organizer
	 * @author Jose Rodriguez
	 * @param serviceName or name of the service to be added
	 * @param organizerName or name of the organizer where service will be added
	 * @param sClient Selenium client connection
	 * @return Boolean true if the organizer was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addWinService(String serviceName, String organizerName, DefaultSelenium sClient) throws Exception
	{
		//Click Service organizer
		sClient.click("//span[@class='node-text' and text()='" + organizerName + "']");
		//Add service at organizer
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		sClient.click("//span[text()='Add Service']");
		Thread.sleep(2000);
		sClient.type("//input[@name='id']", serviceName);
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//table[@class='x-btn   x-btn-noicon ']//button[text()='Submit']")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		sClient.click("//button[text()='Submit']");
		// Refresh Windows Services page to load
		sClient.click("link=Windows Services");
		sClient.waitForPageToLoad("30000");
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//ul[@class='x-tree-node-ct']/li")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//div[@class='x-grid3-body']/div")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		// Click on the Service Organizer
		sClient.click("//span[@class='node-text' and text()='" + organizerName + "']");
		// Wait for Services list to load
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + serviceName + "']")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		boolean result = true;
		
		if (!sClient.isElementPresent("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + serviceName + "']"))
		{
			result = false;
			throw new Exception("Either the service or the service organizer were not found");
		}
		
		return result;		
	}
	
	/*
	 * This method assumes that Windows Services page is already loaded
	 * and inserts a new Service in the WINSERVICE tree root (Not at any organizer)
	 * @author Jose Rodriguez
	 * @param serviceName or name of the service to be added
	 * @param sClient Selenium client connection
	 * @return Boolean true if the organizer was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addWinService(String serviceName, DefaultSelenium sClient) throws Exception
	{
		//Add service
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		sClient.click("//span[text()='Add Service']");
		Thread.sleep(2000);
		sClient.type("//input[@name='id']", serviceName);
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//table[@class='x-btn   x-btn-noicon ']//button[text()='Submit']")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		sClient.click("//button[text()='Submit']");
		// Refresh Windows Services page to load
		sClient.click("link=Windows Services");
		sClient.waitForPageToLoad("30000");
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//ul[@class='x-tree-node-ct']/li")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//div[@class='x-grid3-body']/div")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		// Wait for Services list to load
		for (int second = 0;; second++) {
			if (second >= 60) org.junit.Assert.fail("timeout");
			try { if (sClient.isElementPresent("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + serviceName + "']")) break; } catch (Exception e) {}
			Thread.sleep(1000);
		}

		boolean result = true;
		
		if (!sClient.isElementPresent("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text()='" + serviceName + "']"))
		{
			result = false;
			throw new Exception("The new service was not found");
		}
		
		return result;		
	}
}
