/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Events;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import java.util.*;
import loc.zenoss.*;
import com.thoughtworks.selenium.SeleneseTestCase;
import com.thoughtworks.selenium.DefaultSelenium;

public class AcknowledgeEvent {
	
		private static DefaultSelenium sClient = null;
		private static String[] Severity =  {"Critical","Error","Warning","Info","Debug","Clear"};
		
		
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
		public void acknowledgeEvent() throws Exception{
		
			boolean result = false;
			int count = 0;
			Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			sClient.click("link=Events");
			sClient.waitForPageToLoad("30000");
			// Add one Event
			String summary = "Event2Acknowledge";
			String severity = "Critical";
			String device = "MyDevice";
			String component = "MyComponent";
			String eventclass = "/Status";
			String eventclassKey = "ClassKey";
			result = Event.addSingleEvent(sClient, summary, severity, device, component, eventclass, eventclassKey);
			SeleneseTestCase.assertEquals(true, result);
			//Add multiple Events
			while(count<=20 && result)
			{
				summary = summary + Integer.toString(count);
				severity = getSeverity();
				result = Event.addSingleEvent(sClient, summary, severity, device, component, eventclass, eventclassKey);
				SeleneseTestCase.assertEquals(true, result);
				count++;
			}
			//Get total of current Acknowledge Events
			int ackeventsBefore = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			//Acknowledge some events
			summary = "Event2Acknowledge";
			sClient.mouseMove("//div[@class='x-grid3-body']/div/table/tbody/tr/td/div[text()='"+summary+"']");
			sClient.mouseDown("//div[@class='x-grid3-body']/div/table/tbody/tr/td/div[text()='"+summary+"']");
			sClient.controlKeyDown();
			summary = "Event2Acknowledge10";
			Thread.sleep(4000);
			sClient.mouseMove("//div[@class='x-grid3-body']/div/table/tbody/tr/td/div[text()='"+summary+"']");
			sClient.mouseDown("//div[@class='x-grid3-body']/div/table/tbody/tr/td/div[text()='"+summary+"']");
			sClient.controlKeyUp();
			sClient.click("//table[@id='ack-button']");
			//Get total of Acknowledge Events should be higher than before
			int ackeventsAfter = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			//If we have more Acknowledge Events now than before then we are ok to go
			SeleneseTestCase.assertEquals(true, (ackeventsBefore < ackeventsAfter));
		}
		
		@Test
		public void acknowledgeEventNoSelect() throws Exception{
		
			Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			sClient.click("link=Events");
			sClient.waitForPageToLoad("30000");
			//Get total of Acknowledge Events before hitting Acknowledge button
			int ackeventsBefore = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			sClient.click("//table[@id='ack-button']");
			Thread.sleep(3000);
			//Get total of Acknowledge Events after clicking the Ack button should be the same
			int ackeventsAfter = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			//If we have same Acknowledge Events now than before then we are ok to go
			SeleneseTestCase.assertEquals(true, (ackeventsBefore == ackeventsAfter));
		}
		
		@Test
		public void acknowledgeEventAllSeverity() throws Exception{
		
			Common.Login(sClient, ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			sClient.click("link=Events");
			sClient.waitForPageToLoad("30000");
			sClient.click("//table[@id='severity']");
			// Clear selection states
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Critical']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Error']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Warning']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Info']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Debug']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Clear']");
			Thread.sleep(3000);
			//Display only Critical Events
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='Critical']");
			Thread.sleep(5000);
			//Get total of Acknowledge Events before hitting Acknowledge button
			int ackeventsBefore = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			// Select all events
			sClient.click("//table[@id='select-button']");
			sClient.click("//ul[@class='x-menu-list']/li/a/span[text()='All']");
			// And Acknowledge them
			sClient.click("//table[@id='ack-button']");			
			//Get total of Acknowledge Events after clicking the Acknowledge button
			int ackeventsAfter = sClient.getXpathCount("//table[@class='x-grid3-row-table']/tbody/tr/td/div/div[@class='status-icon-small-acknowledged']").intValue();
			//If we have more Acknowledge Events now than before then we are ok to go
			SeleneseTestCase.assertEquals(true, (ackeventsBefore < ackeventsAfter));
		}
		
		
		private static String getSeverity()
		{
			Random ran = new Random();
			int i = ran.nextInt(5);
			return Severity[i];
		}
		
	}
