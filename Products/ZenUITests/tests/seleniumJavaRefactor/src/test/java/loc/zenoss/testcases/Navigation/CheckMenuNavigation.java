/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Navigation;


import static com.thoughtworks.selenium.SeleneseTestCase.*;
import loc.zenoss.BaseTest;


public class CheckMenuNavigation extends BaseTest {

    public CheckMenuNavigation() {
        super(-1);//TODO: Change TestcaseID
    }

    @Override
    public void script() throws Exception {
        createBackup();
    }

    public void createBackup() throws Exception {
        login();
        click("link=Dashboard");
        waitForPageToLoad();
        sleepThread();    
        assertTrue(isTextPresent("Configure layout..."));
        assertTrue(isTextPresent("Add portlet..."));
        assertTrue(isTextPresent("Stop Refresh"));
        click("link=Events");
        waitForPageToLoad("30000");
        sleepThread();
        assertTrue(isTextPresent("Event Console"));
        assertTrue(isTextPresent("History"));
        assertTrue(isTextPresent("Notifications"));
        click("link=IT Infrastructure");
        waitForPageToLoad("30000");
        sleepThread();
        assertTrue(isTextPresent("Devices"));
        assertTrue(isTextPresent("Network"));
        assertTrue(isTextPresent("Processes"));
        assertTrue(isTextPresent("IP Services"));
        assertTrue(isTextPresent("Windows Services"));
        assertTrue(isTextPresent("Network Map"));
        assertTrue(isTextPresent("Manufacturers"));
        click("link=Reports");
        waitForPageToLoad("120000");
        sleepThread();
        assertTrue(isTextPresent("Report Classes"));
        click("link=Advanced");
        waitForPageToLoad();
        script();
        assertTrue(isTextPresent("Monitoring Templates"));
        assertTrue(isTextPresent("MIBs"));
    }
}
