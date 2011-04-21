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

public class OverrideTemplate {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3575;
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
		public void overrideTemplate() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set variable for Test Template name before and after override
			String templateName =  "FtpMonitor (/Devices)";
			String templateName2 = "FtpMonitor (Locally Defined)";
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
		    //Click on the button "Device Class"
			sClient.click("//button[text()='Device Class']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}
            
			//On the left tree-view list, select the Server/Linux and then the selected template.
			sClient.click("//div[@id='templateTree']//span[text()='Server']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Linux']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Linux']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='" + templateName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='" + templateName + "']");
			sClient.assignId("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']", "tempSourceGrid_Id");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@id='tempSourceGrid_Id']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(5000);
			//Store the table the SourceGrid in a String to be compared later
			String original_SourceGrid = sClient.getEval("window.document.getElementById('tempSourceGrid_Id').innerHTML");
			
			//Do Override
			sClient.click("//table[@id='context-configure-menu']/tbody/tr/td/em/button");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Override Template']");
			sClient.mouseOver("//div[@id='overrideDialog']");
			sClient.mouseOver("//div[@id='overrideDialog']//button[text()='Learn more']");
			//Verify Learn more button and the warning message are displayed
			selenese.verifyTrue(sClient.getText("//div[@id='overrideDialog']/div/div/div/div/div/div/div/div").matches("^exact:Do you wish to override the selected monitoring template[\\s\\S] This will affect all devices using the monitoring template\\.$"));
			selenese.verifyTrue(sClient.isTextPresent("Do you wish to override the selected monitoring template? This will affect all devices using the monitoring template."));
			//Expands the the target drop down menu and select VMware in /Devices
			sClient.click("//div[@id='x-form-el-targetCombo']/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='VMware in /Devices']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='VMware in /Devices']");
			//Click Submit button
			sClient.click("//div[@id='overrideDialog']//button[text()='Submit']");
			Thread.sleep(5000);
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='VMware']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}
			//Go to the device class selected: VMware and verify the selected template is displayed as Locally Defined.
			sClient.click("//div[@id='templateTree']//span[text()='VMware']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='" + templateName2 + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='" + templateName2 + "']");
			
			//Verify that FtpMonitor Template is displayed and has all datasources and templates from the original version.
			//by comparing the content of the datasource tables
			sClient.assignId("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']", "tempSourceGrid2_Id");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@id='tempSourceGrid2_Id']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(7000);
			
			selenese.assertEquals("true", sClient.getEval("window.document.getElementById('tempSourceGrid2_Id').innerHTML.match('" + original_SourceGrid + "') != null;"));

			testCaseResult = "p";
		}

}

