/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.WindowsServices;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;


public class MonitoringWinServices {
	private static int testCaseID = 4143;
	private static String testCaseResult = "f"; //Fail by default
	
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
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
		public void NameOfTheTest() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/Dashboard");
			// Click Infrastructure
			Thread.sleep(1000);
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			// Click Windows Services
			Thread.sleep(3000);
			sClient.click("link=Windows Services");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(3000);
			// Add new WinService
			sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
			sClient.click("ext-comp-1084");
			Thread.sleep(1000);
			sClient.typeKeys("//*[@name='id']", "testWinService");
			Thread.sleep(2000);
			sClient.click("//button[@type='submit']");
			Thread.sleep(30000);
			sClient.typeKeys("name", "testWinService");
			Thread.sleep(10000);
			sClient.clickAt("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text() = 'testWinService']", "testWinService");
			Thread.sleep(3000);
			sClient.typeKeys("descriptionTextField", "new win service");
			Thread.sleep(2000);
			sClient.click("//*[button='Save']");
			// Click Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Add new device
			sClient.doubleClick("//span[@class='node-text' and text()='Server']");
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows']");
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addsingledevice-item");
			sClient.type("add-device-name", "test-win7-1.zenoss.loc");
			Thread.sleep(1000);
			selenese.verifyEquals("/Server/Windows", sClient.getValue("add-device_class"));
			Thread.sleep(2000);
			sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
			Thread.sleep(2000);
			selenese.verifyTrue(sClient.isTextPresent("Add Device Job submitted. View Job Log"));
			Thread.sleep(1000);
			sClient.click("link=View Job Log");
			Thread.sleep(50000);
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("40000");
			// Click on the device added
			Thread.sleep(6000);
			sClient.click("link=test-win7-1.zenoss.loc");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Add Win Service
			sClient.click("//table[@id='component-add-menu']/tbody/tr[2]/td[2]/em");
			// Click on Add Win Service
			sClient.click("addwinservice");
			Thread.sleep(6000);
			sClient.click("//div[@id='winServiceClassLiveSearch']//img");
			Thread.sleep(6000);
			sClient.click("//div[normalize-space(@class) = 'x-combo-list-item' and text()= 'testWinService']");
			selenese.verifyEquals("testWinService", sClient.getValue("ext-comp-1222"));
			sClient.click("//*[button='Submit']");
			Thread.sleep(4000);
			selenese.verifyTrue(sClient.isTextPresent("Add WinService finished successfully"));
			// Verify that win service is displayed in the components section
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Windows Services']");
			Thread.sleep(3000);
			// Verify that the windows service is displayed
			selenese.verifyEquals("testWinService",sClient.getText("link=testWinService"));
			selenese.verifyTrue(sClient.isTextPresent("new win service"));

			testCaseResult = "p";

		}

}
