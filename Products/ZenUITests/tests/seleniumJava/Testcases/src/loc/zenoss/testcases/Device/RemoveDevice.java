/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Device;

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


public class RemoveDevice {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3560;
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
		public void removeDevice() throws Exception{
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/Dashboard");
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Add new Device
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addsingledevice-item");
			Thread.sleep(1000);
			sClient.type("add-device-name", "test-solaris9.zenoss.loc");
			Thread.sleep(1000);
			sClient.typeKeys("add-device_class", "/Server/Solaris");
			Thread.sleep(2000);
			sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
			Thread.sleep(6000);
			sClient.click("link=View Job Log");
			// Job verification
			Thread.sleep(45000);
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(6000);
			// Select the device
			sClient.mouseOver("//div[@class='x-grid3-body']//*[a='test-solaris9.zenoss.loc']");
			sClient.mouseDown("//div[@class='x-grid3-body']//*[a='test-solaris9.zenoss.loc']");
			// Click on Remove Devices
			Thread.sleep(1000);
			sClient.click("delete-button");
			// Click on Remove button
			Thread.sleep(1000);
			sClient.click("//*[button='Remove']");
			Thread.sleep(6000);
			selenese.verifyTrue(sClient.isTextPresent("Successfully deleted device: test-solaris9.zenoss.loc"));
			Thread.sleep(5000);
			// Verify that the device is removed
			selenese.verifyFalse(sClient.isElementPresent("test-solaris9.zenoss.loc"));
						
			testCaseResult = "p";

		}

}
