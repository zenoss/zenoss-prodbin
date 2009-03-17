###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import transaction
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile
from Products.ZenWidgets import messaging
from Products.ZenUtils import Ext
from Products.CMFCore.utils import getToolByName

class SetAdminPasswordException(Exception):
    """There was a problem setting the admin password"""

class CreateUserView(BrowserView):
    """
    Creates the initial user and sets the admin password.
    """
    __call__ = ZopeTwoPageTemplateFile('templates/createuser.pt')

    @Ext.form_action
    def createUser(self):
        """
        Handles form submission for setting the admin password and creating
        an initial user.
        """
        response = Ext.FormResponse()

        adminPassword = self.request.form.get("admin-password1")
        userName = self.request.form.get("username")
        userPassword = self.request.form.get("password1")
        emailAddress = self.request.form.get("emailAddress")

        zenUsers = getToolByName(self.context, 'ZenUsers')

        # Set admin password
        try:
            admin = zenUsers.getUserSettings('admin')
            admin.manage_editUserSettings(password=adminPassword,
                                          sndpassword=adminPassword)
        except:
            response.error('admin-pass',
                       "There was a problem setting the admin password.")

        if not zenUsers.checkValidId(userName) == True:
            response.error('username', 'That username already exists.')
        else:
            ret = zenUsers.manage_addUser(userName, userPassword, 
                              ('ZenManager',), REQUEST=None, email=emailAddress)
            if ret is None:
                response.error('username',
                               'We were unable to add a user at this time.'
                               ' Check your installation.')

        if not response.has_errors():
            # Log out, so the form can log us in as the new user
            acl_users = self.context.getPhysicalRoot().acl_users
            self.context.acl_users.resetCredentials(
                self.request, self.request.response)

        # Don't run the quickstart next time
        self.context.dmd._rq = True

        # Send us on our way
        response.redirect('qs-step2')
        return response
