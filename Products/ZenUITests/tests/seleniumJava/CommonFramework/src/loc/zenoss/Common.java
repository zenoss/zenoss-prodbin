package loc.zenoss;
import com.thoughtworks.selenium.DefaultSelenium;


public class Common {

	public static void openUrl(DefaultSelenium sClient, String url)
	{
		sClient.open(url);	
		
	}
	

	public static void Login(DefaultSelenium sClient, String username, String password) throws Exception
	{
		sClient.open("/");
		sClient.type("username", username);
		sClient.type("__ac_password", password);	
		sClient.click("submitbutton");
		sClient.waitForPageToLoad("40000");
	}
}
