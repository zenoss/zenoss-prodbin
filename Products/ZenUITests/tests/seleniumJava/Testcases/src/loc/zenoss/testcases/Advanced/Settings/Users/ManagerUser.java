package loc.zenoss.testcases.Advanced.Settings.Users;

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


public class ManagerUser {
	
	private static int testCaseID = 1801;
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
		public void managerUser() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			sClient.open("/zport/dmd/?submitted=true");
			// Click on Advanced
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Click Users
			sClient.click("link=Users");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Click on Add new User
			sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
			sClient.type("new_id", "testing001");
			sClient.type("email", "testing001@test.zenoss.com");
			// Click on Ok button
			sClient.click("dialog_submit");
			sClient.click("dialog_submit");
			// Verify that the user is created
			selenese.verifyTrue(sClient.isTextPresent("User \"testing001\" has been created."));
			//  Verify if the user and email are displayed on Users page
			selenese.verifyTrue(sClient.isTextPresent("testing001"));
			selenese.verifyTrue(sClient.isTextPresent("testing001@test.zenoss.com (test)"));
			// Click on the new user
			sClient.click("link=testing001");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(6000);
			// // Type new password
			sClient.type("password", "123");
			sClient.type("sndpassword", "123");
			sClient.removeSelection("roles:list", "label=ZenManager");
			// elect ZenManager role
			sClient.addSelection("roles:list", "label=ZenManager");
			sClient.removeSelection("roles:list", "label=ZenUser");
			// Enter password of the current user
			sClient.type("pwconfirm", "zenoss");
			// Click on Save button
			sClient.click("formsave");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// Verify text that is indicating that the changes were saved
			selenese.verifyTrue(sClient.isTextPresent("Saved at time:"));
			// // Sign Out
			sClient.click("link=sign out");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(5000);
			// // Log In with the new ZenManager user
			sClient.type("username", "testing001");
			sClient.type("__ac_password", "123");
			// Click on Log in button
			sClient.click("submitbutton");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(9000);
			// Verify that the new user is displayed on the dashboard
			selenese.verifyTrue(sClient.isTextPresent("testing001"));
			testCaseResult = "p";
		}

}
