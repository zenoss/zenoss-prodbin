package loc.zenoss.testcases.Events;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class CreateEvent {
	
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
		public void createEvent() throws Exception{
		
			
			Common.Login(sClient,ZenossConstants.adminUserName, ZenossConstants.adminPassword);
			Thread.sleep(10000);
			sClient.click("link=Events");
			sClient.waitForPageToLoad("30000");
			sClient.click("ext-gen40");
			sClient.type("ext-comp-1075", "This is a test event");
			sClient.type("ext-comp-1076", "test-rhel54-64-3");
			sClient.click("ext-gen139");
			sClient.click("//div[@id='ext-gen150']/div[1]");
			sClient.click("ext-gen121");

			
			
		}
		
		
		

		
		

	}


