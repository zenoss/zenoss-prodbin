import os
from random import random
from datetime import datetime
try:
    set
except NameError:
    from sets import Set as set

from OFS.Folder import Folder
from Products.PluggableAuthService import plugins
from Products.PluggableAuthService import interfaces
from Products.PluggableAuthService import PluggableAuthService

from Products import ZenModel

ZENOSS_ROLES = ['ZenUser', 'ZenMonitor']


def backupACLUserFolder(context):
    timestamp = datetime.now().strftime('%Y.%d.%m-%H%M%S')
    randomBit = int(random() * 10000)
    backupFolderName = 'backup_acl_users_%s-%d' % (timestamp, randomBit)
    backupFolder = Folder(backupFolderName)
    backupFolder._setObject('acl_users', context.acl_users)
    context._setObject(backupFolder.getId(), backupFolder)
    context._delObject('acl_users')
    return backupFolderName


def _createInitialUser(self):
    """
    Note: copied and adapted from AccessControl.User.BasicUser

    If there are no users or only one user in this user folder,
    populates from the 'inituser' file in the instance home.
    We have to do this even when there is already a user
    just in case the initial user ignored the setup messages.
    We don't do it for more than one user to avoid
    abuse of this mechanism.
    Called only by OFS.Application.initialize().
    """
    from AccessControl.User import readUserAccessFile

    plugins = self.plugins.listPlugins(
        interfaces.plugins.IUserEnumerationPlugin)
    userCounts = [ len(plugin.listUserInfo()) for id, plugin in plugins ]

    if len(userCounts) <= 1:
        info = readUserAccessFile('inituser')
        if info:
            import App.config
            name, password, domains, remote_user_mode = info
            userManagers = self.plugins.listPlugins(interfaces.plugins.IUserAdderPlugin)
            roleManagers = self.plugins.listPlugins(interfaces.plugins.IRolesPlugin)
            for pluginId, userPlugin in userManagers:
                # delete user
                try:
                    userPlugin.removeUser(name)
                except KeyError:
                    # user doesn't exist
                    pass
                # recreate user
                userPlugin.doAddUser(name, password)
                # add role
                for pluginId, rolePlugin in roleManagers:
                    rolePlugin.assignRoleToPrincipal('Manager', name)
            cfg = App.config.getConfiguration()
            # now that we've loaded from inituser, let's delete the file
            try:
                os.remove(os.path.join(cfg.instancehome, 'inituser'))
            except:
                pass


def createPASFolder(context):
    # check to see if we need to monkey patch PAS to accomodate inituser files
    pas = PluggableAuthService.PluggableAuthService
    if not hasattr(pas, '_createInitialUser'):
        pas._createInitialUser =  _createInitialUser

    # create new PAS
    PluggableAuthService.addPluggableAuthService(context)
    context.acl_users.title = 'PAS'


def setupBasciAuthHelper(context):
    acl = context.acl_users
    id = 'basicAuthHelper'
    if not hasattr(acl, id):
        plugins.HTTPBasicAuthHelper.addHTTPBasicAuthHelper(acl, id)
    interfaces = []
    physPath = '/'.join(context.getPhysicalPath())
    if physPath == '':
        interfaces = ['IExtractionPlugin', 'IChallengePlugin',
            'ICredentialsResetPlugin']
    elif physPath == '/zport':
        interfaces = ['IExtractionPlugin', 'IChallengePlugin']
    acl.basicAuthHelper.manage_activateInterfaces(interfaces)


def setupCookieHelper(context):
    acl = context.acl_users
    id = 'cookieAuthHelper'
    if not hasattr(acl, id):
        plugins.CookieAuthHelper.addCookieAuthHelper(acl, id)
    interfaces = []
    # note that we are only enabling CookieAuth for the Zenoss portal
    # acl_users, not for the root acl_users.
    physPath = '/'.join(context.getPhysicalPath())
    if physPath == '':
        interfaces = ['IExtractionPlugin']
    elif physPath == '/zport':
        interfaces = ['IExtractionPlugin', 'ICredentialsUpdatePlugin',
            'ICredentialsResetPlugin', 'IChallengePlugin']
    acl.cookieAuthHelper.manage_activateInterfaces(interfaces)


def setupRoleManager(context):
    acl = context.acl_users
    id = 'roleManager'
    if not hasattr(acl, id):
        plugins.ZODBRoleManager.addZODBRoleManager(acl, id)
    acl.roleManager.manage_activateInterfaces(['IRolesPlugin',
        'IRoleEnumerationPlugin', 'IRoleAssignerPlugin'])
    # setup roles
    for role in ZENOSS_ROLES:
        try:
            acl.roleManager.addRole(role)
        except KeyError:
            # that role already exists
            pass


def setupUserManager(context):
    acl = context.acl_users
    id = 'userManager'
    if not hasattr(acl, id):
        plugins.ZODBUserManager.addZODBUserManager(acl, id)
    acl.userManager.manage_activateInterfaces(['IAuthenticationPlugin',
        'IUserEnumerationPlugin', 'IUserAdderPlugin'])


def setupTypeSniffer(context):
    acl = context.acl_users
    id = 'requestTypeSniffer'
    if not hasattr(acl, id):
        plugins.RequestTypeSniffer.addRequestTypeSnifferPlugin(acl, id)
    acl.requestTypeSniffer.manage_activateInterfaces(['IRequestTypeSniffer'])


def setupProtocolChooser(context):
    acl = context.acl_users
    id = 'protocolChooser'
    if not hasattr(acl, id):
        plugins.ChallengeProtocolChooser.addChallengeProtocolChooserPlugin(acl,
            id)
    acl.protocolChooser.manage_activateInterfaces([
        'IChallengeProtocolChooser'])
    protocolMapping = {}
    # set up non-Browser protocols to use HTTP BasicAuth
    physPath = '/'.join(context.getPhysicalPath())
    if physPath == '':
        protocolMapping = {
            'Browser': ['http'],
            'FTP': ['http'],
            'WebDAV': ['http'],
            'XML-RPC': ['http'],
        }
    elif physPath == '/zport':
        protocolMapping = {
            'FTP': ['http'],
            'WebDAV': ['http'],
            'XML-RPC': ['http'],
        }
        # we don't want to hard-code plugin names here, so let's do a lookup
        icookie = plugins.CookieAuthHelper.ICookieAuthHelper
        ichallenge = interfaces.plugins.IChallengePlugin
        challenge = [ p for id, p in acl.plugins.listPlugins(ichallenge) ]
        # valid cooike auth plugins
        cookiePlugins = [ p for p in challenge if icookie.providedBy(p) ]
        # we want to move the cookie auth instance above the basic auth listing so
        # that it is accessed first and we can keep 'Browser' set to any; for
        # now, let's just get the first match and use that one (there should
        # really only be one...)
        cookie = cookiePlugins[0]
        index = challenge.index(cookie)
        for i in xrange(index):
            acl.plugins.movePluginsUp(ichallenge, [cookie.id])
    acl.protocolChooser.manage_updateProtocolMapping(protocolMapping)


def setupPASFolder(context):
    setupBasciAuthHelper(context)
    setupCookieHelper(context)
    setupRoleManager(context)
    setupUserManager(context)
    setupTypeSniffer(context)
    # this one has to go last in case any of the protocol mappings need to make
    # reference to an already-installed plugin
    setupProtocolChooser(context)


def replaceACLWithPAS(context, deleteBackup=False):
    # archive the old "User Folder"
    backupId = backupACLUserFolder(context)

    # create a new PAS acl_users
    createPASFolder(context)
    setupPASFolder(context)

    # set up some convenience vars
    orig = getattr(context, backupId).acl_users
    acl = context.acl_users

    # migrate the old user information over to the PAS
    for u in orig.getUsers():
        user, password, domains, roles = (u.name, u.__, u.domains, u.roles)
        acl.userManager.doAddUser(user, password)
        for role in roles:
            acl.roleManager.assignRoleToPrincipal(role, user)
        # initialize UserSettings for each user
        try:
            dmd = context.getPhysicalRoot().zport.dmd
            dmd.ZenUsers.getUserSettings(user)
        except AttributeError:
            # no dmd, or no ZenUsers
            pass

    # delete backup?
    if deleteBackup:
        context._delObject(backupId)


def migratePAS(context):
    # check to see if the current acl_users is a PAS instance or not
    newModule = 'Products.PluggableAuthService.PluggableAuthService'
    try:
        acl = context.acl_users
        # if there's an acl_users object, let's see if theres a login_form
        # attribute; if there is, we need to delete it
        if (hasattr(acl, 'cookieAuthHelper') 
            and hasattr(acl.cookieAuthHelper, 'login_form')):
            acl.cookieAuthHelper._delObject('login_form')
    except AttributeError:
        createPASFolder(context)
        acl = context.acl_users

    if acl.__module__ != newModule:
        replaceACLWithPAS(context)
    else:
        # check to see if there are any missing attributes; we have to make the
        # dir() call twice, because (when testing in the dmd) the 'plugins'
        # attribute doesn't show up on the first call.
        dummy = dir(acl)
        full = set(dir(acl))
        needed = set(['_createInitialUser', 'plugins'])
        # if any of 'needed' are missing, the PAS has to be recreated
        if not full.issuperset(needed):
            backupId = backupACLUserFolder(context)
            backup = context._getOb(backupId)
            createPASFolder(context)
            # now that we have a monkey-patched acl_users, restore the plugins
            for itemId in backup.objectIds():
                acl._setObject(itemId, backup._getOb(itemId))
            # delete the (empty) backup
            context._delObject(backupId)
        # the next function calls all the setup functions, each of which do an
        # attriibute check and installs anything that's missing
        setupPASFolder(context)
