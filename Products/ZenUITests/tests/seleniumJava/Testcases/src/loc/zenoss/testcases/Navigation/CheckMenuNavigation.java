package loc.zenoss.testcases.Navigation;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class CheckMenuNavigation {
	
	
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
		sClient.click("link=Dashboard");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Configure layout..."));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Add portlet..."));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Stop Refresh"));
		sClient.click("link=Events");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Event Console"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("History"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Notifications"));
		sClient.click("link=IT Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Devices"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Network"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Processes"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("IP Services"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Windows Services"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Network Map"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Manufacturers"));
		sClient.click("link=Reports");
		sClient.waitForPageToLoad("120000");
		Thread.sleep(40000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Report Classes"));
		sClient.click("link=Advanced");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		SeleneseTestCase.assertTrue(sClient.isTextPresent("Monitoring Templates"));
		SeleneseTestCase.assertTrue(sClient.isTextPresent("MIBs"));
		
		
	}
	
	
	

	
	

}
