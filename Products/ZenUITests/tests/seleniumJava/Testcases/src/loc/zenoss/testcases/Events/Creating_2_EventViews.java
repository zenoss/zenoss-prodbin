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
package loc.zenoss.testcases.Events;
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

public class Creating_2_EventViews {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 2471;
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
		public void creating_2_EventViews() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variables for Event View #1 and Event View #2
			String eventViewName = "testEventView1";
			String eventViewName2 = "testEventView2";
			// Go to Dashboard > Events
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			// Wait for Event Classes link and click on it
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("link=Users")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("link=Users");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=admin");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Event Views");
			sClient.waitForPageToLoad("30000");
			// Add Event View #1
			sClient.click("//div[@id='menuslot_EventView_list']/table/tbody/tr/td/em");
			Thread.sleep(1000);
			sClient.click("//a[text()='Add Event View...']");
			Thread.sleep(1000);
			sClient.type("//input[@id='new_id']", eventViewName);
			Thread.sleep(1000);
			sClient.click("//input[@id='dialog_submit']");
			// Wait for confirmation of Event View creation
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//tbody[@id='EventViews']//a[text()='" + eventViewName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Open Event View
			sClient.click("//tbody[@id='EventViews']//a[text()='" + eventViewName + "']");
			sClient.waitForPageToLoad("30000");
			// Wait for Event View page to load (Save button displayed)
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//input[@value=' Save ']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Add filter (Relaxed filter criteria): Device class is not /AWS
			sClient.select("add_filter", "label=Device Class");
			sClient.select("deviceClass_mode", "label=is not");
			sClient.select("deviceClass", "label=/AWS");
			// Save event view and go back to Event Views list
			sClient.click("manage_editEventView:method");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Event Views >");
			sClient.waitForPageToLoad("30000");
			// Add Event View #2
			sClient.click("//div[@id='menuslot_EventView_list']/table/tbody/tr/td/em");
			Thread.sleep(1000);
			sClient.click("//a[text()='Add Event View...']");
			Thread.sleep(1000);
			sClient.type("//input[@id='new_id']", eventViewName2);
			Thread.sleep(1000);
			sClient.click("//input[@id='dialog_submit']");
			// Wait for confirmation of Event View creation
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//tbody[@id='EventViews']//a[text()='" + eventViewName2 + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Open Event View
			sClient.click("//tbody[@id='EventViews']//a[text()='" + eventViewName2 + "']");
			sClient.waitForPageToLoad("30000");
			// Wait for Event View page to load (Save button displayed)
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//input[@value=' Save ']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Add filter (Restrictive filter criteria): Device class is neither  /Discovered, /Server/Windows/WMI nor /Server/Linux
			sClient.select("add_filter", "label=Device Class");
			sClient.select("deviceClass_mode", "label=is not");
			sClient.select("deviceClass", "label=/Discovered");
			sClient.select("add_filter", "label=Device Class");
			sClient.select("//span[@id='filters']/table/tbody[1]/tr[2]/td[2]/select", "label=/Server/Windows/WMI");
			sClient.select("add_filter", "label=Device Class");
			sClient.select("//span[@id='filters']/table/tbody[1]/tr[3]/td[2]/select", "label=/Server/Linux");
			// Save event view and go back to Event Views list
			sClient.click("manage_editEventView:method");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Event Views >");
			sClient.waitForPageToLoad("30000");
			// mouseOver to verify that 2 filtered alerting rainbows for the 2 event views show up
			sClient.mouseOver("//tbody[@id='EventViews']/tr/td/div[@class='horizontal-rainbow']/table[contains(@onclick, '" + eventViewName + "')]");
			sClient.mouseOver("//tbody[@id='EventViews']/tr/td/div[@class='horizontal-rainbow']/table[contains(@onclick, '" + eventViewName2 + "')]");
			// Open the second event filter of the rainbow for Event View #1 and wait for the filtered events to show up
			sClient.click("//tbody[@id='EventViews']/tr/td/div/table[contains(@onclick,'" + eventViewName + "')]/tbody/tr/td[2]");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div/div/table/tbody/tr/td/div/div[@class='severity-icon-small error']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Go back to Event Views list
			sClient.click("link=Event Views >");
			sClient.waitForPageToLoad("30000");
			// Open the second event filter of the rainbow for Event View #2 and wait for the filtered events to show up
			sClient.click("//tbody[@id='EventViews']/tr/td/div/table[contains(@onclick,'" + eventViewName2 + "')]/tbody/tr/td[2]");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div/div/table/tbody/tr/td/div/div[@class='severity-icon-small error']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Go back to Event Views list
			sClient.click("link=Event Views >");
			sClient.waitForPageToLoad("30000");

			//Count the number of events on the rainbow for Event View #1 and Event View #2
			int sumEventView1 = 0;
			int sumEventView2 = 0;

			for (int i = 1; i <= 5; i++) {
				sumEventView1 += Integer.parseInt(sClient.getText("//tbody[@id='EventViews']/tr/td/div/table[contains(@onclick,'"+eventViewName+"')]/tbody/tr/td[" + i +"]"));
			}
			
			for (int i = 1; i <= 5; i++) {
				sumEventView2 += Integer.parseInt(sClient.getText("//tbody[@id='EventViews']/tr/td/div/table[contains(@onclick,'"+eventViewName2+"')]/tbody/tr/td[" + i +"]"));
			}
			// Verify that the rainbow for Event View #2 has less events than the rainbow for Event View #1
			if (sumEventView1 < sumEventView2)
			{
				org.junit.Assert.fail("Test failed: Event View #2 has more events than Event View #1");
			}

			Thread.sleep(20000);
			testCaseResult = "p";
		}

}

