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

public class AddDevice {
	private SeleneseTestCase selenese = null;
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
		 selenese = new SeleneseTestCase();
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	
	@Test
	public void addSingleDevice() throws Exception
	{
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		
		sClient.click("link=IT Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
		sClient.click("ext-gen57");
		Thread.sleep(5000);
		sClient.click("//span[contains(text(), 'Add a Single Device')]/../..");
		Thread.sleep(10000);
		sClient.type("add-device-name", "test-winxp-1.zenoss.loc");
		sClient.click("ext-gen360");
		sClient.click("//div[@id='ext-gen424']/div[53]");
		sClient.type("ext-comp-1139", "test-winxp-1");
		sClient.click("ext-gen340");
		sClient.click("ext-gen440");
		sClient.waitForPageToLoad("30000");
		selenese.verifyTrue(sClient.isTextPresent("Job completed at 2010-03-24 11:15:50. Result: success."));
		sClient.click("link=Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=IT Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("//ul[@id='ext-gen108']/li[8]/div/a/span/span[1]");
		sClient.click("link=test-winxp-1");
		sClient.waitForPageToLoad("30000");
		selenese.verifyTrue(sClient.isTextPresent("test-winxp-1"));
		selenese.verifyTrue(sClient.isTextPresent("/Server/Windows"));
		
		
	}

}
