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

public class Event {
	
	public static boolean addSingleEvent(DefaultSelenium sClient, String summary,String severity,String device,String component,String eventclass,String eventclassKey) throws Exception
	{
		sClient.click("//table[@id='add-button']");
		Thread.sleep(2000);
		sClient.type("//textarea[@name='summary']", summary);
		sClient.type("//div[@class='x-form-element']//input[@name='device']", device);
		sClient.type("//div[@class='x-form-element']//input[@name='component']", component);
		sClient.type("//input[@name='severity']", severity);
		sClient.type("//input[@name='evclasskey']", eventclassKey);
		sClient.type("//input[@name='evclass']", eventclass);
		sClient.click("//button[text()='Submit']");
		Thread.sleep(4000);
		return sClient.isTextPresent(summary);		
	}

}
