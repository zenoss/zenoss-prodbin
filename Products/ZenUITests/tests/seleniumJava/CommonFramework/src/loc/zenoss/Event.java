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
