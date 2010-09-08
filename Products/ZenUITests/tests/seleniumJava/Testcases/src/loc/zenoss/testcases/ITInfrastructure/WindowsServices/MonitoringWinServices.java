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
	
	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	@BeforeClass
	 public static void setUpBeforeClass() throws Exception {
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
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(9500);
			// Click on Windows Services
			sClient.click("link=Windows Services");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(6500);
			// Add new Win Service
			sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
			sClient.click("ext-gen232");
			sClient.type("ext-comp-1145", "testWinService");
			sClient.click("ext-gen250");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(6500);
			// Filter the results by the new entered WinService
			sClient.type("name", "testWinService");
			// Validate the WinService name
			selenese.verifyEquals("testWinService", sClient.getValue("nameTextField"));
			// Edit the details - Description field
			sClient.type("descriptionTextField", "New windows service");
			// Save button
			sClient.click("ext-gen88");
			// Click on Infrastructure->Device
			sClient.click("link=Devices");
			sClient.waitForPageToLoad("30000");
	
			// Go to Devices->Server/Windows
			sClient.click("//div[@id='extdd-27']/img[1]");
			sClient.click("//div[@id='extdd-57']/img[1]");
			sClient.click("ext-gen280");
			sClient.click("ext-gen77");
			// Add new Windows device
			sClient.click("addsingledevice-item");
			sClient.type("add-device-name", "test-winxp-1.zenoss.loc");
			// Verify windows device class
			selenese.verifyEquals("/Server/Windows/WMI", sClient.getValue("add-device_class"));
			// Click Add button
			sClient.click("ext-gen316");
			// Verify that the new device is added
			sClient.click("link=View Job Log");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(9500);
			selenese.verifyTrue(sClient.isTextPresent("Job completed at"));
			selenese.verifyTrue(sClient.isTextPresent("Result: success"));
			// Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");

			// Verify that the device is displayed on the list
			selenese.verifyTrue(sClient.isTextPresent("test-winxp-1.zenoss.loc"));
			// Click on the device added
			sClient.click("link=test-winxp-1.zenoss.loc");
			sClient.waitForPageToLoad("30000");
			// Set Configuration Properties
			sClient.click("//ul[@id='ext-gen243']/div/li[8]/div/a/span");
			sClient.type("zWinUser", "Administrator");
			sClient.type("zWinPassword", "ZenossQA1");
			sClient.click("saveZenProperties:method");
			// Model the device
			sClient.click("//table[@id='device_configure_menu']/tbody/tr[2]/td[2]/em");
			sClient.click("ext-gen284");

			selenese.verifyTrue(sClient.isTextPresent("Daemon ZenModeler shutting down"));
			// Close Model Device window
			sClient.click("ext-gen303");
			sClient.refresh();
			sClient.waitForPageToLoad("30000");
			// Add new Windows Service
			sClient.click("//table[@id='component-add-menu']/tbody/tr[2]/td[2]/em");
			sClient.click("addwinservice");
			sClient.click("ext-gen845");
			selenese.verifyTrue(sClient.isTextPresent("testWinService"));
			sClient.click("//div[@id='ext-gen848']/div[221]");
			sClient.click("ext-gen832");
			selenese.verifyTrue(sClient.isTextPresent("Add WinService finished successfully"));
			selenese.verifyTrue(sClient.isTextPresent("WinService WinService/serviceclasses/testWinService was added."));
			// Verify the new windows service added
			sClient.click("ext-gen903");
			selenese.verifyTrue(sClient.isTextPresent("testWinService"));
			selenese.verifyTrue(sClient.isTextPresent("New windows service"));
			// Click on the windows service
			sClient.click("link=testWinService");
			sClient.waitForPageToLoad("30000");
			selenese.verifyTrue(sClient.isTextPresent("test-winxp-1.zenoss.loc"));
			selenese.verifyEquals("testWinService", sClient.getValue("nameTextField"));

			testCaseResult = "p";

		}

}
