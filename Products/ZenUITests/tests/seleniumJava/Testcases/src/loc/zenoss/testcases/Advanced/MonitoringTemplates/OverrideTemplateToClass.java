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
package loc.zenoss.testcases.Advanced.MonitoringTemplates;


import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.Device;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class OverrideTemplateToClass {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3722;
	private static String testCaseResult = "f"; //Fail by default
		
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
		public void overrideTemplateToClass() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Define name and add test device at /Ping class
			String pingDeviceName = "pingDeviceTest";
			Device addDevice = new Device("" + pingDeviceName + "",sClient);
			addDevice.add(""+"/Ping"+"");
			Thread.sleep(10000);			
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			// Select template Apache
			sClient.click("//button[text()='Template']");
			Thread.sleep(4);
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']");
			Thread.sleep(4000);
			// Store content of Data Sources table
			String tempSourceGrid_Id = sClient.getAttribute("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']@id");
			String original_SourceGrid = sClient.getEval("window.document.getElementById('" + tempSourceGrid_Id + "').innerHTML");
			// Override template to (Ping in /Devices)
			sClient.click("//table[@id='context-configure-menu']/tbody/tr/td/em/button");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Override Template']");
			sClient.click("//div[@id='x-form-el-targetCombo']/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[text()='Ping in /Devices']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='Ping in /Devices']");
			sClient.click("//div[@id='overrideDialog']//button[text()='Submit']");
			Thread.sleep(8000);
			// verify Apache template has 2 instances: /Server and /Ping
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//img")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//img");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Ping']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Ping']");
			Thread.sleep(4000);
			// Verify template copy has all datasources from the original template
			String tempSourceGrid2_Id = sClient.getAttribute("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']@id");
			selenese.assertEquals("true", sClient.getEval("window.document.getElementById('" + tempSourceGrid2_Id + "').innerHTML == ('" + original_SourceGrid + "');"));
			// Go to Infrastructure and select first device at /devices/ping
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='devices']//span[@class='node-text' and text()='Ping']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(4000);
			sClient.click("//div[@id='devices']//span[@class='node-text' and text()='Ping']");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + pingDeviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + pingDeviceName + "']");
			sClient.waitForPageToLoad("30000");
			// Verify the template copy is available to bind within /devices/ping
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button");
			Thread.sleep(2000);
			sClient.click("//span[text()='Bind Templates']");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout");
				try { if (sClient.isElementPresent("//dt/em[text()='Apache (/Ping)']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//dt/em[text()='Apache (/Ping)']");


			
			testCaseResult = "p";
		}

}

