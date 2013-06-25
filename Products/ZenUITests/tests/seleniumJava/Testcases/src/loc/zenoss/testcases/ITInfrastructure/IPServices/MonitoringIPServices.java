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

public class MonitoringIPServices {

	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;

	private static int testCaseID = 3594;
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
	public void removeDevice() throws Exception{
		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		sClient.open("/zport/dmd/Dashboard");
		// Click Infrastructure
		Thread.sleep(1000);
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		// Click IP Services
		Thread.sleep(3000);
		sClient.click("link=IP Services");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		// Add new IPService
		sClient.click("//table[@id='footer_add_button']/tbody/tr[2]/td[2]/em");
		sClient.click("ext-comp-1084");
		Thread.sleep(1000);
		sClient.typeKeys("//*[@name='id']", "1atestService");
		Thread.sleep(2000);
		sClient.click("//button[@type='submit']");
		Thread.sleep(40000);
		sClient.typeKeys("name", "1atestService");
		Thread.sleep(5000);
		sClient.clickAt("//div[@class='x-grid3-cell-inner x-grid3-col-name' and text() = '1atestService']", "");
		Thread.sleep(8000);
		sClient.typeKeys("descriptionTextField", "new ip service");
		Thread.sleep(2000);
		sClient.click("//*[button='Save']");
		// Click Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		// Add new device
		sClient.doubleClick("//span[@class='node-text' and text()='Server']");
		sClient.click("//span[normalize-space(@class)='node-text' and text()='Linux']");
		sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em");
		sClient.click("addsingledevice-item");
		sClient.type("add-device-name", "test-rhel54.zenoss.loc");
		Thread.sleep(1000);
		selenese.verifyEquals("/Server/Linux", sClient.getValue("add-device_class"));
		Thread.sleep(2000);
		sClient.click("//table[@id='addsingledevice-submit']/tbody/tr[2]/td[2]/em/button");
		Thread.sleep(2000);
		selenese.verifyTrue(sClient.isTextPresent("Add Device Job submitted. View Job Log"));
		Thread.sleep(1000);
		sClient.click("link=View Job Log");
		Thread.sleep(50000);
		// Click on Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		// Click on the device added
		Thread.sleep(6000);
		sClient.click("link=test-rhel54.zenoss.loc");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(2000);
		// Add IP Service
		sClient.click("//table[@id='component-add-menu']/tbody/tr[2]/td[2]/em");
		// Click on Add Win Service
		sClient.click("addipservice");
		Thread.sleep(2000);
		sClient.click("//div[@id='ipServiceClassLiveSearch']//img");
		Thread.sleep(15000);
		sClient.click("//div[normalize-space(@class) = 'x-combo-list-item' and text()= '1atestService']");
		sClient.click("//*[button='Submit']");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("Add IpService finished successfully"));
		// Verify that win service is displayed in the components section
		sClient.click("//span[normalize-space(@class)='node-text' and text()='IP Services']");
		Thread.sleep(3000);
		// Verify that the windows service is displayed
		selenese.verifyEquals("1atestService", sClient.getText("link=testIPService"));
		selenese.verifyTrue(sClient.isTextPresent("1atestService"));

		testCaseResult = "p";
	}
}
