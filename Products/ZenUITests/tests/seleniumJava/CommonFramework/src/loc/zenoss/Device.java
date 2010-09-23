/**
#############################################################################
# This program is part of Zenoss Core, an open source monitoringplatform.
# Copyright (C) 2007, Zenoss Inc.
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
import java.util.*;

public class Device {
		
	private String nameIp;
	public String className;
	public String collector;
	public String title;
	public String productionState;
	public String priority;
	public String snmpCommunity;
	public String snmpPort;
	public String tagNumber;
	public String rackSlot;
	public String serialNumber;
	public String hwManufacturer;
	public String hwProduct;
	public String osManufacturer;
	public String osProduct;
	public String comments;
	private DefaultSelenium sClient;
	private static String errorMessage="";
	
	/* List of all Devices being loaded in the Multiple Add Devices Wizard.
	 * It then will be used to determine the div[index] to use to add the device properly.
	 * */
	
	private static final String[] classes = new String[] {"AIX Server","BIG-IP","Brocade Switch","Check Point",
		"Check Point SPLAT","Cisco ACE","Cisco ASA","Cisco CatOS","Cisco Codec","Cisco IOS","Cisco Nexus",
		"Cisco WLC","Generic Swith/Router","HP-UX Server","Juniper","Linux Server","Linux Server SSH","NetApp Filer",
		"NetScreen","Nortel Passport","Solaris Server","Windows Server WMI","Windows Server"};
	
	
	/*
	 * Creates and initialize a new instance of the Device class using default values and provided device name or ip
	 * @author Wendell Quesada
	 * @param n_ip Name or Ip of the device to be added
	 * @param sClient Selenium client connection
	 * @return A new instance of Device class
	 * */
	
public Device(String nameorip, DefaultSelenium sClient)
	{
		this.nameIp = nameorip;
		this.className = "/";
		this.collector = "localhost";
		this.snmpPort = "161";
		this.productionState = "Production";
		this.priority = "Normal";
		this.title = "";
		this.snmpCommunity = "";
		this.tagNumber = "";
		this.rackSlot = "";
		this.serialNumber = "";
		this.hwManufacturer = "";
		this.hwProduct = "";
		this.osManufacturer = "";
		this.osProduct = "";
		this.comments = "";
		this.sClient = sClient;
	}
	
	/*
	 * Insert and model a Single Device using default values
	 * @author Wendell Quesada
	 * @return true if suceed adding the device, false otherwise 
	 * @throws Generic Excelption
	 */
	public boolean add() throws Exception
	{
		//Go to Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		//Click on + button
		this.sClient.click("//table[@id='adddevice-button']");
		Thread.sleep(3000);
		//Click on Add Single Device
		this.sClient.click("//span[@class='x-menu-item-text' and text()='Add a Single Device...']");
		//Enter Device Name
		this.sClient.type("add-device-name", this.nameIp);
		//Click on Device Class component
		this.sClient.click("//div/input[@id='add-device_class']");
		Thread.sleep(3000);
		//Click on the selected Device Class
		this.sClient.click("//div[@class='x-combo-list-item' and text()='"+this.className+"']");
		//Click on the Add button
		this.sClient.click("//em/button[normalize-space(@class)='x-btn-text' and text()='Add']");
		Thread.sleep(8000);
		return Device.verifyJobTracebacks(this.sClient);		
	}
	
	/*
	 * Look for tracebacks on the top recennt job added to the queue 
	 * @param sClient the DefaultSelenium instance
	 * @return Returns true if Traceback or ERROR are present, false otherwise 
	 * */
	public static boolean verifyJobTracebacks(DefaultSelenium sClient)
	{		
		//Go to Advanced>Jobs
		boolean result = false;
		sClient.click("link=Advanced");
		sClient.waitForPageToLoad("30000");
		sClient.click("link=Jobs");
		sClient.waitForPageToLoad("30000");
		//Click on View Job image
		sClient.click("//img[@title='View the log for this job']");
		sClient.waitForPageToLoad("30000");
		if(sClient.getText("//pre[1]").matches("^[\\s\\S]*Traceback[\\s\\S]*$"))
		{
			result = true;
			Device.errorMessage = "There are Tracebacks on the log";
		}
		else if(sClient.getText("//pre[1]").matches("^[\\s\\S]*ERROR[\\s\\S]*$"))
		{
			 result = true;		
			Device.errorMessage = "There are Errors on the log";
		}
		return result;
	}
	
	/*
	 * Insert and model a Single Device using the specified class and default values
	 * @author Wendell Quesada
	 * @param cname Class where to add the device e.g: /Network/Router/Cisco
	 * @return True if the device was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public boolean add(String cname)
	{		
		boolean result = false;
		this.className = cname;		
		try{
		result = this.add();
		}catch(Exception e){
			result = false;
		}
		return result;
	}
	
	/*
	 * Insert and model a Single Device using default values provided for the 'More..' area and specified class name
	 * It will include any of the other More area elements
	 * @param cname Class name to where to add the device e.g: /Network/Router/Cisco
	 * @author Wendell Quesada
	 * @return true if suceed adding the device, false otherwise 
	 * @throws Generic Exception
	 */
	public boolean addWithAttributes(String cname) throws Exception
	{
		//Go to Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		//Click on + button
		this.sClient.click("//table[@id='adddevice-button']");
		Thread.sleep(3000);
		//Click on Add Single Device
		this.sClient.click("//span[@class='x-menu-item-text' and text()='Add a Single Device...']");
		//Enter Device Name
		this.sClient.type("add-device-name", this.nameIp);
		//Click on Device Class component
		this.sClient.click("//div/input[@id='add-device_class']");
		Thread.sleep(3000);
		//Click on the selected Device Class
		this.sClient.click("//div[@class='x-combo-list-item' and text()='"+this.className+"']");
		//Type values for other fields
		// Enter Production State
		sClient.click("production-combo");
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.productionState +"']");
		// Enter Priority
		sClient.click("//input[@name='priority']");
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.priority+"']");
		//Enter Title
		sClient.type("//input[@name='title']", this.title);
		//Enter SNMPCommunity string
		sClient.type("//input[@name='snmpCommunity']", this.snmpCommunity);
		//Enter SNMP Port
		sClient.type("//input[@name='snmpPort']", this.snmpPort);
		//Enter Tag Number
		sClient.type("//input[@name='tag']", this.tagNumber);
		//Enter Rack Slot
		sClient.type("//input[@name='rackSlot']", this.rackSlot);
		//Enter Serial Number
		sClient.type("//input[@name='serialNumber']", this.serialNumber);
		//Enter Comments
		sClient.type("//textarea[@name='comments']", this.comments);
		//Enter HW Manufacturer
		sClient.click("//input[@name='hwManufacturer']");
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.hwManufacturer+"']");
		//Enter HW Product
		sClient.click("//input[@name='hwProductName']");
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.hwProduct+"']");
		//Enter OS Manufacturer
		sClient.click("//input[@name='osManufacturer']");
		// TODO: Fix the selection for OS Manufacturer
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.osManufacturer+"']");
		//Enter OS Product
		sClient.click("//input[@name='osProductName']");
		sClient.click("//div[@class='x-combo-list-item' and text()='"+this.osProduct+"']");
		//Click on the Add button
		this.sClient.click("//em/button[normalize-space(@class)='x-btn-text' and text()='Add']");
		Thread.sleep(8000);
		return Device.verifyJobTracebacks(this.sClient);
	}
	
	/*
	 * Insert and model a Single Device using default values and the provided class name using context
	 * @author Wendell Quesada
	 * @param cname the Class Name where to add the Device e.g: /Network/Router/Cisco
	 * @return true if suceed adding the device, false otherwise 
	 * @throws Generic Exception
	 */
	public boolean addDeviceAt(String cname) throws Exception
	{
		////Go to Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		//Assume always fails
		boolean result = false;
		//Let's parse the Class Name so we can iterate through it
		String[] subclasses = cname.split("/");
		for(String c : subclasses)
		{
			//Does the classname contains subclasses organizer? We should do double click
			if(c.matches("Server|Network|Power|Printer|Storage|Web|SSH|WMI"))
			{
				this.sClient.doubleClick("//span[@class='node-text' and text()='"+c+"']");
			}
			//Class name doesn't contains suborganizer we should do single click 
			else if(!c.isEmpty())
			{
				this.sClient.click("//span[@class='node-text' and text()='"+c+"']");
			}				
		}
		//Ok Done. Now Follow normal Add Device process
		//Click on + button
		this.sClient.click("//table[@id='adddevice-button']");
		Thread.sleep(3000);
		//Click on Add Single Device
		this.sClient.click("//span[@class='x-menu-item-text' and text()='Add a Single Device...']");
		//Enter Device Name
		this.sClient.type("add-device-name", this.nameIp);
		//Verify if Provided Class name matchs with what is in the Class Name Combo box		
		if(cname.equalsIgnoreCase(this.sClient.getValue("//div/input[@id='add-device_class']")))
		{
			//The Class Name is equals to the one provided Passed Let's add the device
			//Click on the Add button
			this.sClient.click("//em/button[normalize-space(@class)='x-btn-text' and text()='Add']");
			//wait before going to verify job
			Thread.sleep(8000);
			result = Device.verifyJobTracebacks(this.sClient);
		}
		else
		{
			Device.errorMessage = "The Class Name displayed on the Add Device dialog does not match with the one provide-expected";
			result = false;
		}
		return result;
	}
	
	// TODO: If the list of devices is too long.The device is not visible and therefore we can't locate it unless we scroll dow
	/* Remove a device from the list. 
	 * @author Wendell Quesada
	 * @param device Device name or IP to be removed
	 * @param sClient DefaultSelenium instance
	 * @return True if success on removing, false otherwise
	 * @throws Generic Exception Use Device.getErrorMessage() for more details
	 * */
	public static boolean remove(String device, DefaultSelenium sClient) throws Exception
	{
		//Go to Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		// Select the device
		boolean result = false;
		sClient.mouseOver("//div[@class='x-grid3-body']//*[a='"+device+"']");
		sClient.mouseDown("//div[@class='x-grid3-body']//*[a='"+device+"']");
		// Click on Remove Devices
		Thread.sleep(1000);
		sClient.click("delete-button");
		// Click on Remove button
		Thread.sleep(1000);
		sClient.click("//*[button='Remove']");
		if(sClient.isTextPresent("Successfully deleted device: "+device))
		{
			result = true;
		}
		else
		{
			result = false;
			Device.errorMessage = "Device was not deleted successfully";
		}
		return result;
	}
	
	// TODO: If the list of devices is too long.The device is not visible and therefore we can't locate it unless we scroll dow
	/* Remove a device from the list based on the current instace device name or ip. 
	 * @author Wendell Quesada
	 * @param sClient DefaultSelenium instance
	 * @return True if success on removing, false otherwise
	 * @throws Generic Exception Use Device.getErrorMessage() for more details
	 * */
	public boolean remove(DefaultSelenium sClient) throws Exception
	{
		//Go to Infrastructure
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		// Select the device
		boolean result = false;
		sClient.mouseOver("//div[@class='x-grid3-body']//*[a='"+this.nameIp+"']");
		sClient.mouseDown("//div[@class='x-grid3-body']//*[a='"+this.nameIp+"']");
		// Click on Remove Devices
		Thread.sleep(1000);
		sClient.click("delete-button");
		// Click on Remove button
		Thread.sleep(1000);
		sClient.click("//*[button='Remove']");
		if(sClient.isTextPresent("Successfully deleted device: "+this.nameIp))
		{
			result = true;
		}
		else
		{
			result = false;
			Device.errorMessage = "Device was not deleted successfully";
		}
		return result;		
	}
	
	/* Go and open the DetailView Page for the specified device.
	 * @author Wendell Quesada
	 * @param device Devicename to Open in Detail view
	 * @param sClient DefaultSelenium instance
	 * */
	public static void openDetailView(String device,DefaultSelenium sClient)
	{
		//Go to Infrastructure
		//Open Device Detail View		
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("link="+device);
		sClient.waitForPageToLoad("30000");
	}
	
	/* Go and open the DetailView Page for this device instance.
	 * @author Wendell Quesada	
	 * @param sClient DefaultSelenium instance
	 * */
	public void openDetailView(DefaultSelenium sClient)
	{
		//Go to Infrastructure
		//Open Device Detail View		
		sClient.click("link=Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("link="+this.nameIp);
		sClient.waitForPageToLoad("30000");		
	}
	
	/* Add Multiple SNMP Devices only. Using wizard functionallity
	 * @param pair Hastable containing the String pair <devicename,deviceclass> e.g: "device.foo.com","Linux Server"
	 * @param sClient the DefaultSelenium instance
	 * */
	public void addMultipleDevicesManually(Hashtable<String, String> pair, DefaultSelenium sClient) throws Exception	
	{
		//Go to Infrastructure		
		sClient.click("link=Infrastructure");
		//Click on + button
		this.sClient.click("//table[@id='adddevice-button']");
		Thread.sleep(3000);
		//Click on Add Multiple Device
		this.sClient.click("//span[@class='x-menu-item-text' and text()='Add Multiple Devices...']");
		//Wait for Pop Up
		sClient.waitForPopUp("multi_add", "30000");
		Thread.sleep(8000);
		//Key = devicename
		//Value = class
		int count = 0;
		for(Enumeration<String> keys = pair.elements(); keys.hasMoreElements();)
		{
			//Enter Device name
			sClient.type("//input[@name='device_"+Integer.toString(count)+"']",keys.toString());
			//Click on Device Type Combo
			sClient.click("//input[@id='combobox_"+Integer.toString(count)+"']");
			//Select Class Name
			//First determine the right /div[#] index using the instace Device.classes
			int index = Arrays.binarySearch(Device.classes,keys.toString());
			sClient.click("//div[@class='x-combo-list-inner']/div["+Integer.toString(index)+"]");
			
			//Click on + Button
			sClient.click("//button[text()='+']");
			count++;
		}		
	}
	public void setTitle(String title)
	{
		this.title = title;
	}
	public void setCollector(String collector)
	{
		this.collector = collector;
	}
	public void setProductionState(String pstate)
	{
		this.productionState = pstate;
	}
	public void setPriority(String priority)
	{
		this.priority = priority;
	}
	public void setSnmpCommunity(String snmp)
	{
		this.snmpCommunity = snmp;
	}
	public void setSnmpPort(String port)
	{
		this.snmpPort = port;
	}
	public void setTagNumber(String tag)
	{
		this.tagNumber = tag;
	}
	public void setRackSlot(String slot)
	{
		this.rackSlot = slot;
	}
	public void setSerialNumber(String serial)
	{
		this.serialNumber = serial;
	}
	public void setHWManufacturer(String hwmanu)
	{
		this.hwManufacturer = hwmanu;
	}
	public void setHWProduct(String hwpro)
	{
		this.hwProduct = hwpro;
	}
	public void setOSManufacturer(String osmanu)
	{
		this.osManufacturer = osmanu;
	}
	public void setOSProduct(String ospro)
	{
		this.osProduct = ospro;
	}
	public void setComments(String comments)
	{
		this.comments = comments;
	}
	public static String getErrorMessage()
	{
		return Device.errorMessage;
	}
}
