package loc.zenoss.testcases.Backup;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class CreateBackup {
	
	
	private static DefaultSelenium sClient = null;
	
	
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
	}

	@After
	public void tearDown() throws Exception {
	}
	
	@Test
	public void createBackup() throws Exception{
	
		
		Common.Login(sClient,ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		Common.openUrl(sClient, "/zport/dmd/backupInfo");
		Thread.sleep(8000);
		sClient.click("manage_createBackup:method");
		sClient.waitForPageToLoad("250000");
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully"));
		
		
	}
	
	
	

	
	

}
