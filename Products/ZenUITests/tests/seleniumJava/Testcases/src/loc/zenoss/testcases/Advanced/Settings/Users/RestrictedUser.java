/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
*/
package loc.zenoss.testcases.Advanced.Settings.Users;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.Users;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;


public class RestrictedUser {
	
	private static int testCaseID = 1803;
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
		public void managerUser() throws Exception{
			String user = "testing004";
			String pass = "123";
			String sndpass = "123";
			String roleSelected = "ZenUser"; 
		
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
							
			sClient.open("/zport/dmd/?submitted=true");
			// Click on Advanced page
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			
			// Click Users page
			sClient.click("link=Users");
			sClient.waitForPageToLoad("30000");
			
			//Add new user
			Users.addNewUser(sClient, user, "testing004@test.zenoss.com");
			
			// Click on the new user
			sClient.click("link="+user);
			sClient.waitForPageToLoad("30000");
			
			//Edit user without role - New Restricted User
			Users.editUserWithOutRole(sClient, pass, sndpass, roleSelected);
			
			// // Sign Out
			sClient.click("link=sign out");
			sClient.waitForPageToLoad("30000");
			
			// // Log In with the new ZenManager user
			Thread.sleep(3000);
			sClient.type("username", user);
			sClient.type("__ac_password", pass);
			// Click on Log in button
			sClient.click("submitbutton");
			sClient.waitForPageToLoad("30000");
			
			// Verify that the new user is displayed on the dashboard
			Thread.sleep(4000);
			selenese.verifyTrue(sClient.isTextPresent(user));
			selenese.verifyFalse(sClient.isTextPresent("link=Advanced"));
						
			testCaseResult = "p";
		}

}
