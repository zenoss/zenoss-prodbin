/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.IPServices;

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

public class IPServiceNameAlreadyInUse {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;

	private static int testCaseID = 4085;
	private static String testCaseResult = "f"; //Fail by default

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
	public void IpServiceNameAlreadyInUse() throws Exception{
		String ipServiceName = "IpServiceName";

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		// This will add an IP Service at root level.
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		sClient.click("link=IP Services");
		sClient.waitForPageToLoad("30000");
		// Creates an IP Service with the given name
		Thread.sleep(3000);
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		Thread.sleep(2000);
		sClient.click("//span[@class='x-menu-item-text' and text()='Add Service']");
		Thread.sleep(2000);
		sClient.typeKeys("//*[@name='id']", ipServiceName);
		Thread.sleep(2000);
		sClient.click("//button[@type='submit']");
		Thread.sleep(5000);
		// Enter again the same service name
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		Thread.sleep(2000);
		sClient.click("//span[@class='x-menu-item-text' and text()='Add Service']");
		Thread.sleep(2000);
		sClient.typeKeys("//*[@name='id']", ipServiceName);
		// Mouse Over
		Thread.sleep(1000);
		sClient.mouseOver("//input[@name='id']");
		Thread.sleep(1000);
		//verifyTrue(sClient.isTextPresent("That name is invalid: The id \"test1\" is invalid - it is already in use."));
		selenese.verifyTrue(sClient.isTextPresent("The value in this field is invalid"));

		testCaseResult = "p";
	}

}
