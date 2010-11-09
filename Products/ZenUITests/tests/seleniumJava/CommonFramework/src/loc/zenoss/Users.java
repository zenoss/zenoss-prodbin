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

public class Users {

	/*
	 * This method assumes that Users page is already loaded
	 * and create new users. 
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the user was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addNewUser(DefaultSelenium sClient, String newIDUser, String email) throws Exception{
		// Click on Add new User
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		Thread.sleep(2000);
		sClient.click("UserlistaddUser");
		Thread.sleep(2000);
		sClient.type("new_id", newIDUser);
		sClient.type("email", email);
		// Click on Ok button
		sClient.click("dialog_submit");
		//Wait to user is displayed
		Thread.sleep(10000);
		boolean result = true;
		if(sClient.isTextPresent(newIDUser) ){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new user was not created");
		}
		return result;

	}

	/*
	 * This method assumes that Users page is already loaded and the user is created
	 * Delete a user created. 
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean false if the user was not successfully deleted 
	 * @throws Generic Exception
	 */
	public static boolean deleteUser(DefaultSelenium sClient,String idUser ) throws Exception{

		// Click on the user created
		sClient.click("//input[@name='userids:list' and @value='"+idUser+"']");
		// Click on gear menu
		Thread.sleep(1000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// Click on Delete Users
		sClient.click("UserlistdeleteUser");
		Thread.sleep(2000);
		sClient.click("//input[@type='submit']");
		Thread.sleep(6000);
		sClient.isTextPresent("Users were deleted: "+idUser+".");
		Thread.sleep(8000);

		boolean result = false;

		if(sClient.isElementPresent("//a[text()='"+idUser+"']")){
			result = false;
			throw new Exception("The user was not deleted");
		}
		else
		{
			result = true;			
		}
		return result;
	}

	/*
	 * This method assumes that Users page is already loaded and the user is created
	 * This method assumes that the user created is selected
	 * Edit a user created using Role (If the user is ZenUser and you should select Zen , this method does not work)
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean false if the user was not successfully deleted 
	 * @throws Generic Exception
	 */
	public static boolean editUserWithRole(DefaultSelenium sClient,String pass, String sndpass, String role,String roleSelected) throws Exception{
		// Type new password
		Thread.sleep(3000);
		sClient.type("password", ""+pass+"");
		sClient.type("sndpassword", ""+sndpass+"");

		sClient.addSelection("roles:list", "label="+role+"");
		Thread.sleep(2000);
		sClient.removeSelection("roles:list", "label="+roleSelected +"");
		// Enter password of the current user
		sClient.typeKeys("pwconfirm", ZenossConstants.adminPassword);
		// Click on Save button
		sClient.click("formsave");
		sClient.waitForPageToLoad("30000");

		// Verify text that is indicating that the changes were saved
		Thread.sleep(6000);

		boolean result = true;
		if(sClient.isTextPresent("Saved at time:")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The changes was not saved");
		}
		return result;
	}

	/*
	 * This method assumes that Users page is already loaded and the user is created
	 * This method ssumes that the user created is selected
	 * Edit a user created without Role - Restricted User
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean false if the user was not successfully deleted 
	 * @throws Generic Exception
	 */
	public static boolean editUserWithOutRole(DefaultSelenium sClient,String pass, String sndpass, String roleSelected ) throws Exception{
		// Type new password
		Thread.sleep(300);
		sClient.type("password", ""+pass+"");
		sClient.type("sndpassword", ""+sndpass+"");

		// Select ZenManager role
		sClient.removeSelection("roles:list", "label="+roleSelected +"");
		// Enter password of the current user
		//sClient.typeKeys("pwconfirm", "zenoss");
		sClient.typeKeys("pwconfirm", ZenossConstants.adminPassword);
		// Click on Save button
		sClient.click("formsave");
		sClient.waitForPageToLoad("30000");

		// Verify text that is indicating that the changes were saved
		Thread.sleep(6000);

		boolean result = true;
		if(sClient.isTextPresent("Saved at time:")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The changes was not saved");
		}
		return result;
	}


	/*
	 * This method assumes that Users page is already loaded
	 * Create new user Group
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the group was successfully created
	 * @throws Generic Exception
	 */
	public static boolean newUserGroup(DefaultSelenium sClient,String idGroup) throws Exception{

		//Click on the gear menu
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		Thread.sleep(1000);
		//Click on Add new Group
		sClient.click("GrouplistaddUserGroup");
		Thread.sleep(1000);
		//Type the group Id
		sClient.type("new_id", idGroup);
		//Click on Ok Submit button.
		sClient.click("//input[@type='submit']");
		Thread.sleep(4000);

		boolean result = true;
		if(sClient.isTextPresent("Group \""+idGroup+"\" has been created.") ){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new group was not created");
		}
		return result;
	}

	/*
	 * This method assumes that Users page is already loaded
	 * This method assumes that User is already created
	 * This method assumes that Group is already created
	 * Add user to a group
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the user was successfully added to the group selected
	 * @throws Generic Exception
	 */
	public static boolean UserToGroup(DefaultSelenium sClient,String idUser, String idGroup) throws Exception{
		// Add new User to a group
		sClient.click("//input[@name='groupids:list' and @value='"+idGroup+"']");
		// //Click gear menu - Group section
		Thread.sleep(2000);
		Thread.sleep(1000);
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		Thread.sleep(2000);
		sClient.click("GrouplistaddUserToGroups");
		// Click on Add User...
		// Select a user
		Thread.sleep(2000);
		sClient.addSelection("userids", "label="+idUser+"");
		// Click OK button
		sClient.click("//input[@type='submit']");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(3000);
		sClient.isTextPresent("Users "+idUser+" were added to group "+idGroup+".");
		Thread.sleep(2000);

		boolean result = true;

		if(sClient.isElementPresent("//tbody[@id='Groups']//td[text()='"+idUser+"']")){
			result = true;

		}
		else
		{
			result = false;	
			throw new Exception("The user was not added to the selected group");					
		}
		return result;			
	}

}
