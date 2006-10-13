#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='''
This migration script converts Zenoss instances from using old-style,
non-pluggable acl_users "User Folders" to an acl_users based on the
"PluggableAuthenticationService."

Old users, passwords and roles are migrated to PAS with this script.
''' 

__version__ = "$Revision$"[11:-2]

import os

from OFS.Folder import Folder
from Products.PluggableAuthService import plugins
from Products.PluggableAuthService import PluggableAuthService

import Migrate

# XXX
# This is a hack-workaround for PAS until their login form becomes something
# users can easily update
from AccessControl.Permissions import view
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products import ZenModel

def refreshLoginForm(context, instanceName='cookieAuthHelper'):
    '''
    'context' should be an acl_users PAS instance.
    '''
    try:
        helper = getattr(context, instanceName)
    except AttributeError:
        # there expected plugin instance is not here
        return
    objId = 'login_form'

    # let's get the data from the file
    filename = os.path.join(ZenModel.__path__[0], 'skins', 'zenmodel',
        '%s.pt' % objId)
    html = open(filename).read()
    # if there is no difference between the file and the object, our job is
    # done; if there is a difference, update the object with the text from the
    # file system.
    if objId in helper.objectIds():
        zpt = helper._getOb(objId)
        if zpt and zpt.read() == html:
            return
        else:
            zpt.write(html)
            return

    # create a new form
    login_form = ZopePageTemplate(id=objId, text=html)
    login_form.title = 'Zenoss Login Form'
    login_form.manage_permission(view, roles=['Anonymous'], acquire=1)
    helper._setObject(objId, login_form, set_owner=0)

def updateACLUsersLoginForms():
    # XXX need to figure out how to run this so that it doesn't hang zenmigrate
    # but still runs when ZenModel is loaded/imported.
    from Products.ZenUtils.ZCmdBase import ZCmdBase
    dmd = ZCmdBase(noopts=True).dmd
    app = dmd.getPhysicalRoot()
    zport = app.zport
    for context in [app.acl_users, zport.acl_users]:
        refreshLoginForm(context)

class MigrateToPAS(Migrate.Step):
    version = 23.0

    def backupAndCreate(self, context):
        # archive the old "User Folder"
        backupFolder = Folder('backup_acl_users')
        backupFolder._setObject('acl_users', context.acl_users)
        context._setObject(backupFolder.getId(), backupFolder)
        context._delObject('acl_users')

        # create a new PAS acl_users
        PluggableAuthService.addPluggableAuthService(context)
        context.acl_users.title = 'PAS'

        # set up some convenience vars
        orig = context.backup_acl_users.acl_users
        acl = context.acl_users
        dmd = context.getPhysicalRoot().zport.dmd

        # setup the plugins we will need
        plugins.CookieAuthHelper.addCookieAuthHelper(acl, 'cookieAuthHelper')
        plugins.HTTPBasicAuthHelper.addHTTPBasicAuthHelper(
            acl, 'basicAuthHelper')
        plugins.ZODBRoleManager.addZODBRoleManager(acl, 'roleManager')
        plugins.ZODBUserManager.addZODBUserManager(acl, 'userManager')
        plugins.RequestTypeSniffer.addRequestTypeSnifferPlugin(
            acl, 'requestTypeSniffer')
        plugins.ChallengeProtocolChooser.addChallengeProtocolChooserPlugin(
            acl, 'protocolChooser')

        # activate the plugins for the interfaces each will be responsible for;
        # note that we are only enabling CookieAuth for the Zenoss portal
        # acl_users, not for the root acl_users.
        physPath = '/'.join(context.getPhysicalPath())
        if physPath == '':
            interfaces = ['IExtractionPlugin']
        elif physPath == '/zport':
            interfaces = ['IExtractionPlugin', 'ICredentialsUpdatePlugin',
                'ICredentialsResetPlugin']
        acl.basicAuthHelper.manage_activateInterfaces(['IExtractionPlugin',
            'IChallengePlugin', 'ICredentialsResetPlugin'])
        acl.cookieAuthHelper.manage_activateInterfaces(interfaces)
        acl.roleManager.manage_activateInterfaces(['IRolesPlugin',
            'IRoleEnumerationPlugin', 'IRoleAssignerPlugin'])
        acl.userManager.manage_activateInterfaces(['IAuthenticationPlugin',
            'IUserEnumerationPlugin', 'IUserAdderPlugin'])
        acl.protocolChooser.manage_activateInterfaces([
            'IChallengeProtocolChooser'])

        # set up non-Browser protocols to use HTTP BasicAuth
        protocolMapping = {
            'FTP': 'http',
            'WebDAV': 'http',
            'XML-RPC': 'http',
        }
        acl.protocolChooser.manage_updateProtocolMapping(protocolMapping)

        # migrate the old user information over to the PAS
        for u in orig.getUsers():
            user, password, domains, roles = (u.name, u.__, u.domains, u.roles)
            acl.userManager.addUser(user, user, password)
            for role in roles:
                acl.roleManager.assignRoleToPrincipal(role, user)
            # initialize UserSettings for each user
            dmd.ZenUsers.getUserSettings(user)

    def cutover(self, dmd):
        newModule = 'Products.PluggableAuthService.PluggableAuthService'
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            if context.acl_users.__module__ != newModule:
                self.backupAndCreate(context)
            refreshLoginForm(context.acl_users)

MigrateToPAS()

