/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


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


public class ManagerUser {
	
	private static int testCaseID = 1801;
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
			String user = "testing001";
			String pass = "123";
			String sndpass = "123";
			String role = "ZenManager";
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
			Users.addNewUser(sClient, user, "testing001@test.zenoss.com");
			
			// Click on the new user
			sClient.click("link="+user);
			sClient.waitForPageToLoad("30000");
			
			//Edit user
			Users.editUserWithRole(sClient, pass, sndpass, role, roleSelected);
			
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
			selenese.verifyTrue(sClient.isTextPresent("link=Advanced"));
			
			testCaseResult = "p";
		}

}
