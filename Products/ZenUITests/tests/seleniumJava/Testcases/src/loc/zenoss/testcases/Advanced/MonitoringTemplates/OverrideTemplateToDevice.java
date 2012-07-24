/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Advanced.MonitoringTemplates;


import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.Device;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class OverrideTemplateToDevice {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 3728;
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
		public void overrideTemplateToDevice() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Define name of test devices to be added at /Server/Linux class
			String testDeviceName = "test-tomcat_01";
			String testDeviceName2 = "test-tomcat_02";
			
			//Open page
			sClient.open("/zport/dmd/Dashboard");
			
			//Added 2 test devices
			Device addDevice = new Device("" + testDeviceName + "",sClient);
			addDevice.add(""+"/Server/Linux"+"");
			
			addDevice = new Device("" + testDeviceName2 + "",sClient);
			addDevice.add(""+"/Server/Linux"+"");
			
			Thread.sleep(10000);	

			//Go to Advanced > Infrastructure
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			
			// Open Device details for first test device
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='devices']//span[@class='node-text' and text()='Server']/../../../../../div/img")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(4000);
			sClient.click("//div[@id='devices']//span[@class='node-text' and text()='Server']/../../../../../div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='devices']//span[@class='node-text' and text()='Linux']/")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(1000);
			sClient.click("//div[@id='devices']//span[@class='node-text' and text()='Linux']/");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName + "']");
			sClient.waitForPageToLoad("30000");
			// Open gear menu and click on 
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button");
			Thread.sleep(2000);
			sClient.click("//span[text()='Override Template Here']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='overrideTemplatesDialog']/div/div/div/div/div/div/img")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='overrideTemplatesDialog']/div/div/div/div/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='Apache (/Server)']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='Apache (/Server)']");
			sClient.click("//div[@id='overrideTemplatesDialog']//button[text()='Submit']");
			Thread.sleep(8000);
			// Go to Monitorng Templates and expand Apache template
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			sClient.click("//button[text()='Template']");
			// verify Apache template has the instances: /Server and /Server/${testDeviceName}
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//img")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server/Linux/" + testDeviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server/Linux/" + testDeviceName + "']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server']");
			Thread.sleep(4000);
			// Store content of Data Sources table (for Apache in /Server)
			String tempSourceGrid_Id = sClient.getAttribute("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']@id");
			String original_SourceGrid = sClient.getEval("window.document.getElementById('" + tempSourceGrid_Id + "').innerHTML");
			// Verify template copy ( Apache in /Server/${testDeviceName ) has all datasources from the original template
			sClient.click("//div[@id='templateTree']//span[text()='Apache']/../../..//span[text()='/Server/Linux/" + testDeviceName + "']");
			Thread.sleep(4000);
			String tempSourceGrid2_Id = sClient.getAttribute("//div[@id='dataSourceTreeGrid']//table[@class='x-treegrid-root-table']@id");
			selenese.assertEquals("true", sClient.getEval("window.document.getElementById('" + tempSourceGrid2_Id + "').innerHTML == ('" + original_SourceGrid + "');"));
			// Go to Infrastructure and select the device at /Server/Linux (${testDeviceName})
			sClient.click("link=Infrastructure");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='devices']//span[@class='node-text' and text()='Server']/../../../../../div/img")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(4000);
			sClient.click("//div[@id='devices']//span[@class='node-text' and text()='Server']/../../../../../div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='devices']//span[@class='node-text' and text()='Linux']/")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			Thread.sleep(1000);
			sClient.click("//div[@id='devices']//span[@class='node-text' and text()='Linux']/");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName + "']");
			sClient.waitForPageToLoad("30000");
			// Verify the template copy is available to bind for the test device
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button");
			Thread.sleep(2000);
			sClient.click("//span[text()='Bind Templates']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//dt/em[text()='Apache (/Server/Linux/" + testDeviceName + ")']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//dt/em[text()='Apache (/Server/Linux/" + testDeviceName + ")']");
			// Go back to /Server/Linux class and and select another device ( ${testDeviceName2} )
			sClient.click("link=/Server/Linux");
			sClient.waitForPageToLoad("30000");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName2 + "']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='device_grid']//div[@class='x-grid3-body']/div/table/tbody/tr/td/div/a[text()='" + testDeviceName2 + "']");
			sClient.waitForPageToLoad("30000");
			// Verify the template copy is NOT available to bind for this device
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//table[@class='x-btn x-btn-icon' and @id='device_configure_menu']//button");
			Thread.sleep(2000);
			sClient.click("//span[text()='Bind Templates']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='bindTemplatesDialog']//dl[1]")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			selenese.assertFalse(sClient.isElementPresent("//dt/em[text()='Apache (/Server/Linux/" + testDeviceName + ")']"));

			
			testCaseResult = "p";
		}

}
