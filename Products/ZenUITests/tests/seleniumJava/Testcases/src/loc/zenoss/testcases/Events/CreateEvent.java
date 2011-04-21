/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
 */
package loc.zenoss.testcases.Events;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.*;

import com.thoughtworks.selenium.SeleneseTestCase;
import com.thoughtworks.selenium.DefaultSelenium;

public class CreateEvent {

	private static DefaultSelenium sClient = null;
	private static String testCaseResult = "f"; //Fail by default
	private static int testCaseID = 2493;

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
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
	}

	@After
	public void tearDown() throws Exception {
	}

	@Test
	public void createEvent() throws Exception{

		boolean result = false;
		Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
		sClient.click("link=Events");
		sClient.waitForPageToLoad("30000");
		// Add one Event
		String summary = "MySummary";
		String severity = "Critical";
		String device = "MyDevice";
		String component = "MyComponent";
		String eventclass = "/Status";
		String eventclassKey = "ClassKey";
		result = Event.addSingleEvent(sClient, summary, severity, device, component, eventclass, eventclassKey);
		SeleneseTestCase.assertEquals(true, result);	

		testCaseResult = "p";
	}		

}


