/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Networks;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddNetwork {
	private SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	private String network;
		
	
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
		//Login into System
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		//Go to INFRASTRUCTURE
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		//Click on Networks
		sClient.click("link=Networks");
		sClient.waitForPageToLoad("30000");
		//Click Add Button and wait for pop up window
		sClient.click("ext-gen35");
		Thread.sleep(5000);
		//Enter value of Network
		sClient.type("ext-comp-1168", network);
		//Submmit
		sClient.click("ext-gen356");
		//Verify Network was added properly
		sClient.click("link=Dashboard");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		//Click on Networks
		sClient.click("link=Networks");
		sClient.waitForPageToLoad("30000");
		selenese.verifyTrue(sClient.isTextPresent(network));		
	}

}
