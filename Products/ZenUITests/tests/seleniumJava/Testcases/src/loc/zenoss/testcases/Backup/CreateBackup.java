/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Backup;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class CreateBackup {
	
	
	private static DefaultSelenium sClient = null;

	private static int testCaseID;
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
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	@Test
	public void createBackup() throws Exception{
		
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("manage_createBackup:method");
		sClient.waitForPageToLoad("250000");
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));
		
		/**DELETE THE BACKUP CREATED**/
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("fileNames:list");
		sClient.click("ext-gen16");
		sClient.click("BackupFileslistdeleteBackup");
		Thread.sleep(12000);
		sClient.click("manage_deleteBackups:method");
		sClient.waitForPageToLoad("30000");	
	}
	/**
	 * Create a Backup whit DefaultSettings Testcase 1822
	 * @throws Exception
	 */
	@Test
	public void  createBackupDefaultSettings() throws Exception{
		//TODO Add devices and run console commands
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		testCaseID = 1822;
		
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("manage_createBackup:method");
		sClient.waitForPageToLoad("250000");
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));
		
		/**DELETE THE BACKUP CREATED**/
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("fileNames:list");
		sClient.click("ext-gen16");
		sClient.click("BackupFileslistdeleteBackup");
		Thread.sleep(12000);
		sClient.click("manage_deleteBackups:method");
		sClient.waitForPageToLoad("30000");	
		
		testCaseResult = "p";
     	 
	}
	/**
	 * Create a Backup WithOut Mysql Login Testcase 1826
	 * @throws Exception
	 */
	@Test
	public void  createBackupWithOutMysqlLogin() throws Exception{
		//TODO Add devices and run console commands
		
		testCaseID = 1826;
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("includeMysqlLogin");
		sClient.click("manage_createBackup:method");
		sClient.waitForPageToLoad("250000");
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));
		
		/**DELETE THE BACKUP CREATED**/
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("fileNames:list");
		sClient.click("ext-gen16");
		sClient.click("BackupFileslistdeleteBackup");
		Thread.sleep(12000);
		sClient.click("manage_deleteBackups:method");
		sClient.waitForPageToLoad("30000");	
		
		testCaseResult = "p";
	}
	/**
	 * Create Backup Without MySQL events  Testcase 1824
	 * @throws Exception
	 */
	@Test
	public void  createBackupWithOutMySQLevents () throws Exception{
		//TODO Add devices and run console commands
		
		testCaseID = 1824;
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("includeEvents");
		sClient.click("manage_createBackup:method");
		sClient.waitForPageToLoad("250000");
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));	
		
		/**DELETE THE BACKUP CREATED**/
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.open("/zport/dmd/Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.open("/zport/dmd/backupInfo");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(12000);
		sClient.click("fileNames:list");
		sClient.click("ext-gen16");
		sClient.click("BackupFileslistdeleteBackup");
		Thread.sleep(12000);
		sClient.click("manage_deleteBackups:method");
		sClient.waitForPageToLoad("30000");	
		
		testCaseResult = "p";
	}



	
}
