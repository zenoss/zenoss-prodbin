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
	public static final String browser = (System.getProperties().containsKey("Browser"))?System.getProperties().getProperty("Browser") : "Compatible FF";//"Compatible FF";//System.getProperty("Browser");// 
	/**
	 * The machine in which the test will be executed
	 */
	public static final String targetMachine=(System.getProperties().containsKey("TargetMachine"))?System.getProperties().getProperty("TargetMachine") : "test-rhel54-32-5.zenoss.loc";
	public static final String testedMachine="http://" + targetMachine +":8080";
	
	public static final String build=(System.getProperties().containsKey("ZenossBuild"))?System.getProperties().getProperty("ZenossBuild") : "777";
	public static final String version=(System.getProperties().containsKey("ZenossVersion"))?System.getProperties().getProperty("ZenossVersion") : "777";
	public static final String installationPath=(System.getProperties().containsKey("buildLocation"))?System.getProperties().getProperty("buildLocation") : "777";
	
	/**
	 * The ssh parameters
	 */
	
	public static final String sshUser=(System.getProperties().containsKey("SSHUser"))?System.getProperties().getProperty("SSHUser") : "tat";
	public static final String sshPass=(System.getProperties().containsKey("SSHPass"))?System.getProperties().getProperty("SSHPass") : "mypass";
	
}
