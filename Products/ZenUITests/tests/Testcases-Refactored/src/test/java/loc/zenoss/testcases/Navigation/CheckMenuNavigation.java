/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#############################################################################
 */
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
