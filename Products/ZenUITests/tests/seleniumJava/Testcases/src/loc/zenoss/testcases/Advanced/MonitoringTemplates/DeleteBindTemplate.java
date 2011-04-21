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
package loc.zenoss.testcases.Advanced.MonitoringTemplates;

import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class DeleteBindTemplate {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 4214;
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
		public void deleteBindTemplate() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set variable for Testing Template name
			String templateName = "e_testTemplate";
			String dataSourceName = "testDataSource";
			String deviceName = "colo2800.zenoss.loc";
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			// Add new template (Devices in Devices)
			sClient.click("//table[@id='footer_add_button']//button[@class=' x-btn-text add']");
			sClient.type("//input[@name='id']", templateName);
			// Click Template Path list, wait for list to populate and select "Devices in Devices"
			sClient.click("//html/body/div[@id='addNewTemplateDialog']//form/div[2]/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='Devices in Devices']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='Devices in Devices']");
			Thread.sleep(5000);
			sClient.click("//button[text()='Submit']");
			Thread.sleep(5000);
			// Wait for templates list to refresh and show the new template
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//span[text()='" + templateName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//span[text()='/Devices']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(2000);
			// Add new Data Source
			sClient.click("//table[@id='datasourceAddButton']/tbody/tr/td/em/button");
			sClient.type("dataSourceName", dataSourceName);
			Thread.sleep(1000);
			// Select SNMP in the Data Source Type list and click Submit
			sClient.type("//input[@id='dataSourceTypeCombo']", "SNMP");
			Thread.sleep(1000);
			sClient.click("//button[text()='Submit']");
			for (int second = 0;; second++) {
				if (second >= 60) org.junit.Assert.fail("timeout: New Datasource not found");
				try { if (sClient.isElementPresent("//html/body/div/div/div/div/div/div/div/div/div/div/div/div/div/div/table/tbody/tr/td/a/span[text()='" + dataSourceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//html/body/div/div/div/div/div/div/div/div/div/div/div/div/div/div/table/tbody/tr/td/img");
			// Wait for DataSource to show up
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//html/body/div/div/div/div/div/div/div/div/div/div/div/div/div/div/table/tbody/tr/td/table/tbody/tr/td/a/span[text()='" + dataSourceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Go to Infrastructure tab and open a Device
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + deviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + deviceName + "']");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@id='device_configure_menu' and  @class='x-btn x-btn-icon']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Bind the new template on the device
			sClient.click("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button");
			Thread.sleep(2000);
			sClient.click("//span[text()='Bind Templates']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//dt/em[text()='" + templateName + " (/Devices)']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//dt/em[text()='" + templateName + " (/Devices)']");
			sClient.doubleClick("//dt/em[text()='" + templateName + " (/Devices)']");
			sClient.click("//div[@id='bindTemplatesDialog']//button[text()='Save']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='" + templateName + " (/Devices)']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Go back to monitoring templates and delete the template
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//a/span[text()='" + templateName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//a/span[text()='" + templateName + "']");
			Thread.sleep(2000);
			sClient.click("//a/span[text()='" + templateName + "']/../../../ul/li/div/a/span");
			Thread.sleep(2000);
			sClient.click("//button[@class=' x-btn-text delete']");
			Thread.sleep(1000);
			sClient.click("//button[text()='OK']");
			// Wait for confirmation message to show up in the top of the page
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[contains(., " + templateName + ") and @class='x-flare-message']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Go back to Infrastructure and open the device 
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + deviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + deviceName + "']");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//a/span[text()='Monitoring Templates']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(4000);
			// Verify the template is not binded any more
			selenese.assertFalse(sClient.isElementPresent("//a/span[text()='" + templateName + " (/Devices)']"));
			// End
			
			Thread.sleep(1000);
			testCaseResult = "p";
		}

}

