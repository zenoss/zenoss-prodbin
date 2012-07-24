/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Devices;

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

public class AssignDeviceToGroup {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3463;
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
			
			String deviceName = "test-win7-18.zenoss.loc";
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Add new device of class /Server/Windows
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			Thread.sleep(4000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows']");
			Thread.sleep(4000);
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addsingledevice-item");
			sClient.type("add-device-name", deviceName);
			sClient.click("add-device-protocol");
			selenese.verifyEquals("/Server/Windows", sClient.getValue("add-device_class"));
			Thread.sleep(2000);
			sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
			// Create test group 1
			sClient.click("//span[@class='node-text' and text()='Groups']");
			Thread.sleep(2000);
			sClient.click("//button[normalize-space(@class)='x-btn-text add']");
			sClient.type("id", "testGroup1");
			sClient.type("description", "Group for test purposes");
			Thread.sleep(2000);
			sClient.click("//button[normalize-space(@class)='x-btn-text' and text()='Submit']");
			Thread.sleep(2000);
			// Create test group 2
			sClient.click("//span[@class='node-text' and text()='Groups']");
			sClient.click("//button[normalize-space(@class)='x-btn-text add']");
			sClient.type("id", "testGroup2");
			sClient.type("description", "Group for test purposes");
			Thread.sleep(2000);
			sClient.click("//button[normalize-space(@class)='x-btn-text' and text()='Submit']");
			// Drag and drop new device into testGroup1
			Thread.sleep(40000);
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			Thread.sleep(4000);
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows']");
			Thread.sleep(4000);
			sClient.mouseDownAt("link=" + deviceName, "10,20");
			Thread.sleep(1000);
			sClient.mouseMoveAt("//span[normalize-space(@class)='node-text' and text()='testGroup1']", "10,20");
			Thread.sleep(1000);
			sClient.mouseOver("//span[normalize-space(@class)='node-text' and text()='testGroup1']");
			Thread.sleep(1000);
			sClient.mouseUpAt("//span[normalize-space(@class)='node-text' and text()='testGroup1']", "10,20");
			Thread.sleep(2000);
			sClient.click("//button[normalize-space(@class)='x-btn-text' and text()='OK']");
			Thread.sleep(2000);
			// Move device from testGroup1 to testGroup2
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			sClient.click("//span[normalize-space(@class)='node-text' and text()='testGroup1']");
			Thread.sleep(3000);
			sClient.mouseDownAt("link=" + deviceName, "10,20");
			Thread.sleep(1000);
			sClient.mouseMoveAt("//span[normalize-space(@class)='node-text' and text()='testGroup2']", "100,1000");
			Thread.sleep(1000);
			sClient.mouseOver("//span[normalize-space(@class)='node-text' and text()='testGroup2']");
			Thread.sleep(1000);
			sClient.mouseUpAt("//span[normalize-space(@class)='node-text' and text()='testGroup2']", "20,-10");
			Thread.sleep(2000);
			sClient.click("//button[normalize-space(@class)='x-btn-text' and text()='OK']");
			// Verify device class is not affected
			sClient.click("//span[normalize-space(@class)='node-text' and text()='testGroup2']");
			Thread.sleep(4000);
			sClient.click("link=" + deviceName);
			sClient.waitForPageToLoad("30000");
			Thread.sleep(4000);
			selenese.verifyTrue(sClient.isElementPresent("link=/Server/Windows"));
			
			testCaseResult = "p";
		}

}
