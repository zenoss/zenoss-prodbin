/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss;


public class ZenossConstants {

	
	/**
	 * Admin user name 
	 */
	public static final String adminUserName="admin";
	/**
	 * Admin password
	 */
	public static final String adminPassword="zenoss";
	/**
	 * Localhost
	 */
	public static final String SeleniumHubHostname = (System.getProperties().containsKey("SeleniumServerHost"))?System.getProperties().getProperty("SeleniumServerHost") : "localhost";
	public static final String SeleniumHubPort = (System.getProperties().containsKey("SeleniumServerPort"))?System.getProperties().getProperty("SeleniumServerPort") : "4444";
	
	/**
	 * Browser in which the testcase will be executed
	 */
	
	public static final String browser = (System.getProperties().containsKey("Browser"))?System.getProperties().getProperty("Browser") : "*firefox3";//"Compatible FF";//System.getProperty("Browser");// 
	
	/**
	 * The machine in which the test will be executed
	 */
	
	public static final String targetMachine=(System.getProperties().containsKey("TargetMachine"))?System.getProperties().getProperty("TargetMachine") : "test-rhel5-32-3.zenoss.loc";
	public static final String testedMachine="http://" + targetMachine +":8080";
	
	public static final String build=(System.getProperties().containsKey("ZenossBuild"))?System.getProperties().getProperty("ZenossBuild") : "629";
	public static final String version=(System.getProperties().containsKey("ZenossVersion"))?System.getProperties().getProperty("ZenossVersion") : "2.5.70";
	public static final String installationPath=(System.getProperties().containsKey("buildLocation"))?System.getProperties().getProperty("buildLocation") : "/629/";
	
	/**
	 * The ssh parameters
	 */
	
	public static final String sshUser=(System.getProperties().containsKey("SSHUser"))?System.getProperties().getProperty("SSHUser") : "tat";
	public static final String sshPass=(System.getProperties().containsKey("SSHPass"))?System.getProperties().getProperty("SSHPass") : "mypass";
	
	/**
	 * Testlink Parameters
	 */
	public static final String TestLinkAPIKEY = (System.getProperties().containsKey("TestLinkAPIKEY"))?System.getProperties().getProperty("TestLinkAPIKEY") : "x1254slokdijwur8882jjfuJJhhsu2";
	public static final String TestLinkAPIURL = (System.getProperties().containsKey("TestLinkAPIURL"))?System.getProperties().getProperty("TestLinkAPIURL") : "http://dev.zenoss.com/testlink/lib/api/xmlrpc.php";
	public static final int testPlanID = (System.getProperties().containsKey("testPlanID"))? Integer.parseInt(System.getProperties().getProperty("testPlanID")) : 3838;
	
	
}
