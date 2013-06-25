/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Device;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddDeviceRelations {
	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	private String Devicename = "";
		
	
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)   {
        	public void open(String url) {
        		commandProcessor.doCommand("open", new String[] {url,"true"});
        	}
        };
		sClient.start();
		sClient.deleteAllVisibleCookies();
	}

	@AfterClass
	public static void tearDownAfterClass() throws Exception {
		sClient.stop();
	}

	@Before
	public void setUp() throws Exception {
		 selenese = new SeleneseTestCase();		 
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	
	@Test
	public void addSingleDevice() throws Exception
	{
		//Login into System
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		//Go to INFRASTRUCTURE
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		//Click on Add Device Button
		sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
		//Click on Single Device
		sClient.click("ext-gen247");
		//Enter Devicename or IP
		sClient.type("add-device-name", Devicename);
		//Click on DeviceClass Combobox
		sClient.click("ext-gen292");
		//Select Server/Linux entry
		sClient.click("//div[@id='ext-gen356']/div[43]");
		//Click on More
		sClient.click("link=More...");
		//Click on HW Man and select Intel
		sClient.click("ext-gen449");
		sClient.click("//div[@id='ext-gen478']/div[23]");
		// Click on HW Product and select Intel Celeron Model 4 Stepping 9
		sClient.click("ext-gen453");
		sClient.click("//div[@id='ext-gen480']/div[8]");
		// Click on OS Man and selected RedHat
		sClient.click("ext-gen457");
		sClient.click("//div[@id='ext-gen483']/div[39]");
		// Click on OS Product and selected REL ES 4.3
		sClient.click("ext-gen410");
		sClient.click("//div[@id='ext-gen488']/div[43]");
		//Click on Submitt
		sClient.click("ext-gen272");
		//Wait until we get the job notification
		Thread.sleep(5000);
		sClient.waitForPageToLoad("30000");
		//Verify notification message
		selenese.verifyTrue(sClient.isTextPresent("View Job Log"));
		//Verify Device was properly added
		sClient.click("link=Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		selenese.verifyTrue(sClient.isTextPresent(Devicename));		
	}

}
