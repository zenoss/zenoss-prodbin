/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss;

import com.thoughtworks.selenium.DefaultSelenium;

import java.util.Locale;
import java.util.ResourceBundle;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.junit.Test;

import static loc.zenoss.util.Constants.*;

/**
 *
 * @author wquesada
 */
public abstract class BaseTest {

    private static DefaultSelenium sClient = null;
    private static ResourceBundle bundle = ResourceBundle.getBundle("settings",Locale.US);
    private static ResourceBundle strings = ResourceBundle.getBundle("strings",Locale.US);
    protected int testCaseId = 0;

    /**
     * Try to avoid constructor in unit testing
     * @param testCaseId
     */
    protected BaseTest(int testCaseId) {
        System.out.println("Running Once");
        this.testCaseId = testCaseId;
        if (sClient == null) {
            sClient = new DefaultSelenium(bundle.getString("SeleniumServerHost"),
                    Integer.parseInt(getString(SELENIUM_SERVER_PORT)),
                    getString(BROWSER),
                    getString(TEST_MACHINE)) {

                @Override
                public void open(String url) {
                    commandProcessor.doCommand("open", new String[]{url, "true"});
                }
            };
            sClient.start();
            sClient.deleteAllVisibleCookies();
        }
        System.out.println("start");
    }

    @Test
    public void testScript() {
        try {     
            script();
            preCloseConnection();
            closeConnection();
            postCloseConnection();
        } catch (Exception ex) {
            Logger.getLogger(BaseTest.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    public abstract void script() throws Exception;

    protected static String getString(String key) {
        return bundle.getString(key);
    }

    /**
     * Client Functionality
     */
    protected void click(String arg, Object... vars) {
        String clickable = null;

        if (vars != null && vars.length > 0) {
            clickable = String.format(arg, vars);
        } else {
            clickable = arg;
        }
        sClient.click(clickable);
    }
    
    protected void doubleClick(String arg, Object... vars) {
        String clickable = null;

        if (vars != null && vars.length > 0) {
            clickable = String.format(arg, vars);
        } else {
            clickable = arg;
        }
        sClient.doubleClick(clickable);
    }

    protected boolean isTextPresent(String text) {
        return sClient.isTextPresent(text);
    }

    protected void preCloseConnection() {
    }

    protected void closeConnection() {
        sClient.stop();

    }

    protected void postCloseConnection() {
    }

    protected void sleepThread(int time) {
        try {
            Thread.sleep(time);
        } catch (InterruptedException ex) {
            Logger.getLogger(BaseTest.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    protected void sleepThread() {
        sleepThread(DEFAULT_THREAD_SLEEP_TIME);
    }

    protected void login() {
        try {
            Common.Login(sClient, getString(ADMIN_USER_NAME), getString(ADMIN_PASSWORD));
        } catch (Exception ex) {
            Logger.getLogger(BaseTest.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    protected void open(String url) {
        sClient.open(url);
    }

    /**
     * Handy method to get Strings from string.properties files without to much code effort
     * @param key
     * @return
     */
    public String $(String key) {
        return strings.getString(key);
    }

    protected void waitForPageToLoad(String time) {
        sClient.waitForPageToLoad(time);
    }

    protected void waitForPageToLoad() {
        waitForPageToLoad(DEFAULT_PAGE_WAIT_TIME);
    }
}
