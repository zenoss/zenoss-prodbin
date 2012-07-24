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

public class SetPriority {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3771;
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
		public void setPriority() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/Dashboard");
			// Click Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Click buttons [Add devices] > [Add Multiple Devices...]
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
			sClient.click("addmultipledevices-item");
			sClient.waitForPopUp("multi_add", "30000");
			sClient.selectWindow("name=multi_add");
			// Select [Autodiscovered devices]
			sClient.click("autoradio");
			// Enter IP range and click OK
			sClient.type("ext-comp-1003", "10.175.211.3-5");
			sClient.click("//div[@id='autodiscoverform']//button[text()='Discover']");
			sClient.selectWindow("null");
			// Wait 60 s for devices to be discovered
			Thread.sleep(60000);
			// Click Infrastructure to refresh the page
			sClient.click("link=Infrastructure");
			Thread.sleep(8000);
			// Select Discovered class in the left panel
			sClient.click("//span[normalize-space(@class)='node-text' and text()='Discovered']");
			Thread.sleep(3000);
			// Click [Select] button and then [All] option
			sClient.click("//*[button='Select']");
			sClient.click("//span[@class='x-menu-item-text' and text()='All']");
			// Click the [Actions] button and then [Set Priority...] option
			sClient.click("//table[@id='actions-menu']/tbody/tr[2]/td[2]/em");
			sClient.click("//span[normalize-space(@class)='x-menu-item-text' and text()='Set Priority...']");
			// Click Priority combobox
			sClient.click("priority");
			Thread.sleep(5000);
			// Select [Trivial] option and Click [OK]
			sClient.click("//div[normalize-space(@class) = 'x-combo-list-item' and text() = 'Trivial']");
			sClient.click("//table[@id='priorityok']/tbody/tr[2]/td[2]");
			// Click on the device esxwin2.zenoss.loc from the list
			sClient.click("link=esxwin2.zenoss.loc");
			Thread.sleep(8000);
			// Verify device's priority is set to Trivial
			selenese.verifyEquals("Trivial", sClient.getValue("priority"));
			// Go back to /Discovered class list
			sClient.click("//a[@class='z-entity' and text() = '/Discovered']");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Click on the device kvm.zenoss.loc from the list
			sClient.click("link=kvm.zenoss.loc");
			Thread.sleep(8000);
			// Verify device's priority is set to Trivial
			selenese.verifyEquals("Trivial", sClient.getValue("priority"));
			// Go back to /Discovered class list
			sClient.click("//a[@class='z-entity' and text() = '/Discovered']");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(8000);
			// Click on the device vpn.zenoss.loc from the list
			sClient.click("link=vpn.zenoss.loc");
			Thread.sleep(8000);
			// Verify device's priority is set to Trivial
			selenese.verifyEquals("Trivial", sClient.getValue("priority"));
			
			testCaseResult = "p";
		}

}
