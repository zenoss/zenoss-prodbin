package loc.zenoss.testcases.Dashboard;
import java.util.Arrays;
import java.util.List;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class VerifyAddPortlets {	
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 1790;
	private static String testCaseResult = "f"; //Fail by default
	private static int testPlanID = (System.getProperties().containsKey("testPlanID"))? Integer.parseInt(System.getProperties().getProperty("testPlanID")) : 2403;
		
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)  {
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
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}	
	
	@Test
	public void testAddPortlets() throws Exception{		
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
		
		List<String> portlets = Arrays.asList("Device Issues", "Location", "Zenoss Issues", "Production States", "Site Window", "Root Organizers", "Messages", "Object Watch List");  
		int count = 2;
		for (String portlet : portlets)
		{
			sClient.open("http://test-cent4-64-1.zenoss.loc:8080/zport/dmd?submitted=");		
		
			sClient.click("link=Add portlet...");
			Thread.sleep(5000);
			sClient.click("yui-gen"+(count++)+"-button");
			
			Thread.sleep(5000);
			SeleneseTestCase.assertTrue(sClient.isTextPresent(portlet));
			
		}
		testCaseResult = "p";
	}
}
