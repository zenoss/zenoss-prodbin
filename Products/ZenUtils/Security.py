import os
from random import random
from datetime import datetime

from OFS.Folder import Folder
from Products.PluggableAuthService import plugins
from Products.PluggableAuthService import PluggableAuthService

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

def backupACLUserFolder(context):
    timestamp = datetime.now().strftime('%Y.%d.%m-%H%M%S')
    randomBit = int(random() * 10000)
    backupFolderName = 'backup_acl_users_%s-%d' % (timestamp, randomBit)
    backupFolder = Folder(backupFolderName)
    backupFolder._setObject('acl_users', context.acl_users)
    context._setObject(backupFolder.getId(), backupFolder)
    context._delObject('acl_users')
    return backupFolderName

def createPASFolder(context):
    PluggableAuthService.addPluggableAuthService(context)
    context.acl_users.title = 'PAS'

    # set up some convenience vars
    acl = context.acl_users

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

def replaceACLWithPAS(context):
    # archive the old "User Folder"
    backupId = backupACLUserFolder(context)

    # create a new PAS acl_users
    createPASFolder(context)

    # set up some convenience vars
    orig = getattr(context, backupId).acl_users
    acl = context.acl_users

    # migrate the old user information over to the PAS
    for u in orig.getUsers():
        user, password, domains, roles = (u.name, u.__, u.domains, u.roles)
        acl.userManager.addUser(user, user, password)
        for role in roles:
            acl.roleManager.assignRoleToPrincipal(role, user)
        # initialize UserSettings for each user
        try:
            dmd = context.getPhysicalRoot().zport.dmd
            dmd.ZenUsers.getUserSettings(user)
        except AttributeError:
            # no dmd, or no ZenUsers
            pass
