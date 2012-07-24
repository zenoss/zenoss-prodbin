/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


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

public class EditThresholds {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3730;
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
		public void editThresholds() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set variable for Testing Template and Threshold name
			String templateName = "w_testTemplate";
			String thresholdName = "testThreshold";
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			sClient.click("//button[text()='Template']");
			Thread.sleep(4000);
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']/div/div/ul/div/li[1]/div/a/span")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Add new template
			sClient.click("//table[@id='footer_add_button']//button[@class=' x-btn-text add']");
			sClient.type("//input[@name='id']", templateName);
			// Click Template Path list, wait for list to populate and select "Linux in Devices/Server"
			sClient.click("//html/body/div[@id='addNewTemplateDialog']//form/div[2]/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='Linux in Devices/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(2000);
			sClient.click("//div[text()='Linux in Devices/Server']");
			Thread.sleep(2000);
			sClient.click("//button[text()='Submit']");
			// Wait for templates list to refresh and show the new template
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//span[text()='" + templateName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//span[text()='/Server/Linux']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Click the Add Threshold button
			sClient.click("//table[@id='thresholdAddButton']//button");
			// Click the type list, wait for list to populate and select "MinMaxThreshold" type
			sClient.click("//html/body/div[@id='addThresholdDialog']//form/div/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='MinMaxThreshold']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='MinMaxThreshold']");
			Thread.sleep(1000);
			// Type the desired threshold name and click on Add button
			sClient.type("//input[@name='thresholdIdField']", thresholdName);
			Thread.sleep(1000);
			sClient.click("//button[text()='Add']");
			// Wait for the new threshold to show up and click on it
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.mouseDown("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			sClient.mouseUp("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			// Click the button to Edit the new threshold
			sClient.click("//table[@id='thresholdEditButton']//button");
			// Wait for Edit Threshold Dialog to show up
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='editThresholdDialog']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			selenese.verifyTrue(sClient.isElementPresent("//div[@id='thresholdItemSelector']"));
			// Type Max, Min values as 100 and 1
			sClient.type("//input[@name='minval']", "1");
			sClient.type("//input[@name='maxval']", "100");
			// Select the Event Class as /App
			sClient.click("//input[@name='eventClass']/../img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//html/body/div/div/div[text()='/App']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//html/body/div/div/div[text()='/App']");
			// Type Escalate count as 10
			sClient.type("//input[@name='escalateCount']", "10");
			// Save the threshold and wait for edit threshold dialogue to go away
			sClient.click("//button[text()='Save']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (!sClient.isElementPresent("//div[@id='editThresholdDialog']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// Open the edit threshold dialogue again and verify that the just saved information is present 
			sClient.mouseDown("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			sClient.mouseUp("//div[@id='thresholdGrid']//td/div[text()='" + thresholdName + "']");
			sClient.click("//table[@id='thresholdEditButton']//button");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='editThresholdDialog']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			selenese.assertEquals("1", sClient.getValue("//input[@name='minval']"));
			selenese.assertEquals("100", sClient.getValue("//input[@name='maxval']"));
			selenese.assertEquals("/App", sClient.getValue("//input[@name='eventClass']/../input"));
			selenese.assertEquals("10", sClient.getValue("//input[@name='escalateCount']"));
			// END
		
			Thread.sleep(1000);
			testCaseResult = "p";
		}

}
