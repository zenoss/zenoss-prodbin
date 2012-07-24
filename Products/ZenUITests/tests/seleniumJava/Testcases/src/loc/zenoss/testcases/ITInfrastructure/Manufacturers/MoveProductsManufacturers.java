/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Manufacturers;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.Manufacturers;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class MoveProductsManufacturers {
	private static int testCaseID = 3883;
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
	public void createManufacturer() throws Exception{
		String manufacturer = "testMoveProducts";
		String url = "testURL.com";
		String address1 = "testAddress";
		String city = "San Jose";
		String country = "Costa Rica";
		String state= "San Jose";
		String zip = "00000";
		String hardware = "testHardware";
		String software = "testSoftware";
		String os = "testOS"; 

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		//Click Infrastructure
		sClient.click("link=Infrastructure");
		Thread.sleep(8000);

		// Click on Manufacturers
		sClient.click("link=Manufacturers");
		sClient.waitForPageToLoad("30000");

		//Create new manufacturer
		Manufacturers.createManufacturers(sClient, manufacturer);

		// Click on the manufacturer
		sClient.click("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']");
		// Click on Edit button
		Thread.sleep(5000);
		sClient.click("link=Edit");
		sClient.waitForPageToLoad("30000");
		// Add URL
		Thread.sleep(2000);
		sClient.type("url", url);
		sClient.type("address1",address1 );
		sClient.type("city", city);
		sClient.type("country", country);
		sClient.type("state", state);
		sClient.type("zip",zip);
		Thread.sleep(2000);
		// Click on Save button
		sClient.click("//input[@value=' Save ']");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("Saved at time:"));
		// Click on Overview
		sClient.click("link=Overview");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+manufacturer+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td/a[text()='"+url+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+address1+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+state+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+country+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+zip+"']"));

		//Add new Hardware
		Manufacturers.addNewHarware(sClient, hardware);
		Thread.sleep(2000);

		//Add new Software
		Manufacturers.addNewSoftware(sClient, software);
		Thread.sleep(2000);

		//Add new Operating System
		Manufacturers.addNewOS(sClient, os);
		Thread.sleep(2000);
		//Move Products
		// Select the products
		Thread.sleep(2000);
		sClient.click("//input[@type='checkbox' and @value='"+hardware+"']");
		sClient.click("//input[@type='checkbox' and @value='"+os+"']");
		sClient.click("//input[@type='checkbox' and @value='"+software+"']");
		// Click gear menu
		Thread.sleep(2000);
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		// Click Move to Manufacturer
		Thread.sleep(1000);
		sClient.click("ProductlistmoveToManufacturer");
		// Select new manufacturer
		Thread.sleep(2000);
		sClient.clickAt("moveTarget", "");
		Thread.sleep(2000);
		// Select new Manufacturer
		sClient.select("moveTarget", "label=ATI");
		Thread.sleep(2000);
		// Click on Move Button
		Thread.sleep(1000);
		sClient.click("//input[@type='submit']");
		Thread.sleep(3000);
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+software+"']"));
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Software']"));
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+os+"']"));
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Operating System']"));
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+hardware+"']"));
		selenese.verifyFalse(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Hardware']"));
		// Click Manufacturers
		sClient.click("link=Manufacturers");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(4000);
		// Select the manufacturer selected
		sClient.click("link=ATI");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(6000);
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+software+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Software']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+os+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Operating System']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+hardware+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Hardware']"));

		testCaseResult = "p";
	}
}
