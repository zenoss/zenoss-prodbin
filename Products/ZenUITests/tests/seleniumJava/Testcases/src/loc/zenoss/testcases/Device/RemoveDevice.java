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
	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3560;
	private static String testCaseResult = "f"; //Fail by default
		
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
		public void removeDevice() throws Exception{
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			//Dashboard page
		    sClient.open("/zport/dmd/Dashboard");
		    //Click on Infrastructure
		    sClient.click("link=Infrastructure");
		    sClient.waitForPageToLoad("30000");
		    Thread.sleep(9500);
		    sClient.click("//div[@id='extdd-27']/img[1]");
		    //Go to Device Class Solaris
		    sClient.click("ext-gen260");
		    //Click on Add new single device
		    sClient.click("ext-gen77");
		    sClient.click("ext-gen281");
		    //Verify that the correct class is selected on the device class dropdown list
		    selenese.verifyEquals("/Server/Solaris", sClient.getValue("add-device_class"));
			sClient.click("ext-gen312");
			//Add new Solaris device
			sClient.type("add-device-name", "test-solaris9.zenoss.loc");
			//Click on view job log link.
			sClient.click("link=View Job Log");
			sClient.waitForPageToLoad("30000");
			//Verify that the device is being created
			Thread.sleep(12000);
			selenese.verifyTrue(sClient.isTextPresent("DeviceCreationJob \"/opt/zenoss/bin/zendisc run --now -d test-solaris9.zenoss.loc --monitor localhost --deviceclass /Server/Solaris --job"));
			selenese.verifyTrue(sClient.isTextPresent("Job completed"));
			// The result should be successfull
			selenese.verifyTrue(sClient.isTextPresent("Result: success"));
			//Click on Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(9500);
			sClient.click("//div[@id='extdd-27']/img[1]");
			//Click on Server/Solaris class
			sClient.click("ext-gen260");
			//Verify that the device is added and using the correct IP address
			selenese.verifyTrue(sClient.isTextPresent("test-solaris9.zenoss.loc"));
			selenese.verifyTrue(sClient.isTextPresent("10.204.210.17"));
			selenese.verifyTrue(sClient.isTextPresent("/Server/Solaris"));
			//Click on Remove Device
			sClient.click("ext-gen79");
			//Click on Remove button 
			sClient.click("ext-gen300");
			//Click on device classes and verify that the device is not present in /Server/Solaris
			selenese.verifyFalse(sClient.isTextPresent("test-solaris9.zenoss.loc"));	
			//Click on device classes and verify that the device is not present.
			sClient.click("ext-gen183");
			selenese.verifyFalse(sClient.isTextPresent("test-solaris9.zenoss.loc"));	
			testCaseResult = "p";

		}

}
