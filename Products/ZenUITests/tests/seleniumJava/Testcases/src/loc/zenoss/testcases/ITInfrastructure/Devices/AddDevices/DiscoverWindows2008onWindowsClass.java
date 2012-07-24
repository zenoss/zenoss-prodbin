/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Devices.AddDevices;

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

public class DiscoverWindows2008onWindowsClass {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 2051;
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
		public void assignDeviceToGroup() throws Exception{
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set a variable for devicename, zWinUser and zWinPassword
			String deviceName = "test-sql2008-1d.zenoss.loc";
			String username = "Administrator";
			String password = "ZenossQA1";
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Add Win2008 device at /Server/Windows
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			Thread.sleep(4000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows']");
			Thread.sleep(4000);
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addsingledevice-item");
			sClient.type("add-device-name", deviceName);
			selenese.verifyEquals("/Server/Windows", sClient.getValue("add-device_class"));
			sClient.click("link=More...");
			sClient.type("snmpCommunity", "public");
			Thread.sleep(2000);
			sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
			// Open the Job Log from the message that shows up in the top
			
			Common.waitForElement("link=View Job Log", sClient);
			sClient.click("link=View Job Log");
			sClient.waitForPageToLoad("30000");
			// Wait for the Job to be complete
			
			//sClient.setTimeout("180000");
			//Common.waitForElement("//body[@class='log-output']", sClient);
			Common.waitForElement("//pre[2]]", sClient);
			//Common.waitForText("//body[@class='log-output']", "^[\\s\\S]*Job completed[\\s\\S]*$", sClient);
			//sClient.setTimeout("30000");

			// Verify that Job Log doesn't show Errors or Tracebacks or 'device already exists' message
			selenese.verifyFalse(sClient.getText("//pre[1]").matches("^[\\s\\S]*Device [\\s\\S]* already exists[\\s\\S]*$"));
			selenese.verifyFalse(sClient.getText("//pre[1]").matches("^[\\s\\S]*Traceback[\\s\\S]*$"));
			selenese.verifyFalse(sClient.getText("//pre[1]").matches("^[\\s\\S]*Error[\\s\\S]*$"));
			Thread.sleep(2000);
			// Go back to Infra and open the new device
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			Thread.sleep(4000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows']");
			Thread.sleep(4000);
			sClient.click("link=" + deviceName);
			sClient.waitForPageToLoad("30000");
			Thread.sleep(4000);
			// Open Configuration Properties
			sClient.click("//span[text()='Configuration Properties']");
			// Set zWinUser and zWinPassword and click Save

			Common.waitForElement("saveZenProperties:method", sClient);

			sClient.type("zWinUser", username);
			sClient.type("zWinPassword", password);
			sClient.click("saveZenProperties:method");

			Common.waitForElement("Configuration properties have been updated.", sClient);
			
			// Model the device
			sClient.click("//table[@id='device_configure_menu']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[text()='Model Device...']");
			// Wait for "Daemon ZenModeler shutting down" so Modeling is finished
			sClient.setTimeout("180000");
			
			Common.waitForText("//div[@class='streaming-container']", "^[\\s\\S]*Daemon ZenModeler shutting down[\\s\\S]*$", sClient);

			sClient.setTimeout("30000");
			// Verify Modeling output has not errors or tracebacks
			selenese.verifyFalse(sClient.getText("//div[@class='streaming-container']").matches("^[\\s\\S]*Error[\\s\\S]*$"));
			selenese.verifyFalse(sClient.getText("//div[@class='streaming-container']").matches("^[\\s\\S]*Traceback[\\s\\S]*$"));
			Thread.sleep(2000);
			sClient.click("//div[@class='x-tool x-tool-close']");
			// Go to device Overview
			sClient.click("//span[text()='Overview']");
			// Verify device status is Up
			selenese.verifyEquals("Up", sClient.getText("//span[@class='status-up-large']"));
			// Verify device has Hardware and OS data
			
			Common.waitForElement("//div[@name='hwManufacturer']", sClient);

			selenese.verifyNotEquals("None", sClient.getText("//div[@name='hwManufacturer']/a"));
			selenese.verifyNotEquals("None", sClient.getText("//div[@name='osManufacturer']/a"));
			Thread.sleep(2000);
			
			// Verify device has Components
			if (!sClient.isElementPresent("//li[@style='']/div/a/span[text()=\"Components\"]"))
			{
				throw new Exception("Element not found: //li[@style='']/div/a/span[text()=\"Components\"]");
			}
			// // Verify device has Hardware and Software data
			sClient.click("//span[text()='Software']");

			Common.waitForElement("//span[text()='Installed Software']", sClient);

			if (!sClient.isElementPresent("//tbody[@id='InstalledSoftware']/tr[2]/td[2]"))
			{
				throw new Exception("Element not found: //tbody[@id='InstalledSoftware']/tr[2]/td[2]");
			}
			// End

			testCaseResult = "p";
		}

}
