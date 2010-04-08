package loc.zenoss.testcases.Backup;


import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class BackupDefaultSettings {

	private static DefaultSelenium sClient = null;

	private static int testCaseID = 1790;
	private static String testCaseResult = "f"; //Fail by default
    
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)  {
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
		//TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	@Test
	public void navigationSettings() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd/Dashboard");
		 sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(12000);
		 sClient.click("manage_createBackup:method");
		 sClient.waitForPageToLoad("250000");
		 SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));
		
	}

}
