#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types

from random import choice

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from AccessControl import getSecurityManager
from Acquisition import aq_base
from Products.PluggableAuthService import interfaces
from zExceptions import Unauthorized
from DateTime import DateTime

from Products.ZenEvents.ActionRule import ActionRule
from Products.ZenEvents.CustomEventView import CustomEventView
from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from AdministrativeRole import DeviceAdministrativeRole, \
                               DevOrgAdministrativeRole
import Products.ZenUtils.Utils as Utils

import smtplib
from email.MIMEText import MIMEText
import socket
import Pager
import sys

UserSettingsId = "ZenUsers"


def manage_addUserSettingsManager(context, REQUEST=None):
    """Create user settings manager."""
    ufm = UserSettingsManager(UserSettingsId)
    context._setObject(ufm.getId(), ufm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


def rolefilter(r): return r not in ("Anonymous", "Authenticated", "Owner")

class UserSettingsManager(ZenModelRM):
    """Manage zenoss user folders.
    """
    
    meta_type = "UserSettingsManager"

    #zPrimaryBasePath = ("", "zport")

    sub_meta_types = ("UserSettings",)

    factory_type_information = (
        {
            'id'             : 'UserSettingsManager',
            'meta_type'      : 'UserSettingsManager',
            'description'    : """Base class for all devices""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addUserSettingsManager',
            'immediate_view' : 'manageUserFolder',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'manageUserFolder'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )


    def getAllUserSettings(self):
        """Return list user settings objects.
        """
        return filter(lambda u: u.id != "admin",
                    self.objectValues(spec="UserSettings"))
            

    def getAllUserSettingsNames(self, filtNames=()):
        """Return list of all zenoss usernames. 
        """
        filt = lambda x: x not in filtNames
        return [ u.id for u in self.getAllUserSettings() if filt(u.id) ]


    def getUsers(self):
        """Return list of Users wrapped in their settings folder.
        """
        users = []
        for uset in self.objectValues(spec="UserSettings"):
            user = self.acl_users.getUser(uset.id)
            if user: users.append(user.__of__(uset))
        return users
            

    def getUser(self, userid=None):
        """Return a user object.  If userid is not passed return current user.
        """
        if userid is None:
            user = getSecurityManager().getUser()
        else:
            user = self.acl_users.getUser(userid)
        if user: return user.__of__(self.acl_users)


    def getAllActionRules(self):
        for u in self.getAllUserSettings():
            for ar in u.getActionRules():
                yield ar

    def getUserSettings(self, userid=None):
        """Return a user folder.  If userid is not passed return current user.
        """
        user=None
        if userid is None:
            user = getSecurityManager().getUser()
            userid = user.getId()
        if not userid: raise Unauthorized
        folder = self._getOb(userid,None)
        if not folder and userid:
            ufolder = UserSettings(userid)
            self._setObject(ufolder.getId(), ufolder)
            folder = self._getOb(userid)
            if not user:
                user = self.getUser(userid)
            if user:
                folder.changeOwnership(user)
                folder.manage_setLocalRoles(userid, ("Owner",))
        return folder


    def getUserSettingsUrl(self, userid=None):
        """Return the url to the current user's folder.
        """
        uf = self.getUserSettings(userid)
        if uf: return uf.getPrimaryUrlPath()
        return ""


    def manage_addUser(self, userid, password=None,roles=("ZenUser",),
                    REQUEST=None,**kw):
        """Add a zenoss user to the system and set its default properties.
        """
        if password is None:
            password = self.generatePassword()
        self.acl_users._doAddUser(userid,password,roles,"")
        user = self.acl_users.getUser(userid)
        ufolder = self.getUserSettings(userid)
        if REQUEST: kw = REQUEST.form
        ufolder.updatePropsFromDict(kw)
        if REQUEST:
            REQUEST['message'] = "User created at time:"
            return self.callZenScreen(REQUEST)
        else:
            return user


    def generatePassword(self):
        """ Generate a valid password.
        """
        # we don't use these to avoid typos: OQ0Il1
        chars = 'ABCDEFGHJKLMNPRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join( [ choice(chars) for i in range(6) ] )


    def manage_changeUser(self, userid, password=None, sndpassword=None,
                          roles=None, domains=None, REQUEST=None, **kw):
        """Change a zenoss users settings.
        """
        user = self.acl_users.getUser(userid)
        if not user:
            if REQUEST:
                REQUEST['message'] = "user %s not found" % userid
                return self.callZenScreen(REQUEST)
            else:
                return
        if password and password != sndpassword:
            if REQUEST:
                REQUEST['message'] = "passwords didn't match no change: "
                return self.callZenScreen(REQUEST)
            else:
                raise ValueError("passwords don't match")
        if password is None: password = user._getPassword()
        if roles is None: roles = user.roles
        if domains is None: domains = user.domains
        self.acl_users._doChangeUser(userid,password,roles,domains)
        ufolder = self.getUserSettings(userid)
        ufolder.updatePropsFromDict(kw)
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)
        else:
            return user


    def manage_deleteUsers(self, userids=(), REQUEST=None):
        """Delete a list of zenoss users from the system.
        """
        # get a list of plugins that can add manage users and then call the
        # appropriate methods
        # 
        # XXX this needs to be reviewed when new plugins are added, such as the
        # LDAP plugin
        ifaces = [interfaces.plugins.IUserAdderPlugin]
        getPlugins = self.acl_users.plugins.listPlugins
        plugins = [ getPlugins(x)[0][1] for x in ifaces ]
        for userid in userids:
            try:
                for plugin in plugins:
                    plugin.removeUser(userid)
            except KeyError:
                # this means that there's no user in the acl_users, but that
                # Zenoss still sees the user; we want to pass on this exception
                # so that Zenoss can clean up
                pass
            if getattr(aq_base(self), userid, False):
                us = self._getOb(userid)
                for ar in us.adminRoles():
                    ar.userSetting.removeRelation()
                    mobj = ar.managedObject().primaryAq()
                    mobj.adminRoles._delObject(ar.id)
                self._delObject(userid)
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)


    def manage_emailTestAdmin(self, userid, REQUEST=None):
        ''' Do email test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_emailTest()
        if msg:
            REQUEST['message'] = msg
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def manage_pagerTestAdmin(self, userid, REQUEST=None):
        ''' Do pager test for given user
        '''
        userSettings = self.getUserSettings(userid)
        msg = userSettings.manage_pagerTest()
        if msg:
            REQUEST['message'] = msg
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def cleanUserFolders(self):
        """Delete orphaned user folders.
        """
        userfolders = self._getOb(UserSettingsId)
        userids = self.acl_users.getUserNames()
        for fid in userfolders.objectIds():
            if fid not in userids:
                userfolders._delObject(fid)
   

    def getAllRoles(self):
        """Get list of all roles without Anonymous and Authenticated.
        """
        return filter(rolefilter, self.valid_roles())




def manage_addUserSettings(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = UserSettings(id, title)
    context._setObject(id, dc)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


addUserSettings = DTMLFile('dtml/addUserSettings',globals())


class UserSettings(ZenModelRM):
    """zenoss user folder has users preferences.
    """

    meta_type = "UserSettings"

    sub_meta_types = ("ActionRule",)

    email = ""
    pager = ""
    defaultPageSize = 40
    defaultEventPageSize = 30
    defaultAdminRole = "Administrator"
    defaultAdminLevel = 1
    oncallStart = 0
    oncallEnd = 0
    escalationMinutes = 0

    _properties = ZenModelRM._properties + (
        {'id':'email', 'type':'string', 'mode':'w'},
        {'id':'pager', 'type':'string', 'mode':'w'},
        {'id':'defaultPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultEventPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultAdminRole', 'type':'string', 'mode':'w'},
        {'id':'defaultAdminLevel', 'type':'int', 'mode':'w'},
        {'id':'oncallStart', 'type':'int', 'mode':'w'},
        {'id':'oncallEnd', 'type':'int', 'mode':'w'},
        {'id':'escalationMinutes', 'type':'int', 'mode':'w'},
    )
 

    _relations =  (
        ("adminRoles", ToMany(ToOne, "AdministrativeRole", "userSetting")),
    )

   # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'editUserSettings',
            'actions'        :
            (
                {'name'          : 'Edit',
                'action'        : 'editUserSettings',
                'permissions'   : ("Change Settings",),
                },
                {'name'          : 'Administered Objects'
                , 'action'        : 'administeredDevices'
                , 'permissions'   : ( "Change Settings", )
                },
                {'name'          : 'Event Views',
                'action'        : 'editEventViews',
                'permissions'   : ("Change Settings",),
                },
                {'name'          : 'Alerting Rules',
                'action'        : 'editActionRules',
                'permissions'   : ("Change Settings",),
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def getUserRoles(self):
        """Get current roles for this user.
        """
        user = self.getUser(self.id)
        if user: return filter(rolefilter, user.getRoles())
        return ()


    security.declareProtected('Change Settings', 'updatePropsFromDict')
    def updatePropsFromDict(self, propdict):
        props = self.propertyIds()
        for k, v in propdict.items():
            if k in props: setattr(self,k,v)


    def iseditable(self):
        """Can the current user edit this settings object.
        """
        owner = self.getOwner()
        user = getSecurityManager().getUser()
        return user.has_role("Manager") or owner == user


    security.declareProtected('Change Settings', 'manage_editUserSettings')
    def manage_editUserSettings(self, password=None, sndpassword=None,
                                roles=None, domains=None,
                                REQUEST=None, **kw):
        """Update user settings.
        """
        # get the user object; return if no user
        user = self.getUser(self.id)
        if not user:
            user = self.getPhysicalRoot().acl_users.getUser(self.id)
        if not user:
            if REQUEST:
                REQUEST['message'] = "user %s not found" % self.id
                return self.callZenScreen(REQUEST)
            else:
                return

        # update role info
        roleManager = self.acl_users.roleManager
        origRoles = filter(rolefilter, user.getRoles())
        # if there's a change, then we need to update
        if roles != origRoles:
            # can we use the built-in set?
            try:
                set()
            except NameError:
                from sets import Set as set
            # get roles to remove and then remove them
            removeRoles = list(set(origRoles).difference(set(roles)))
            for role in removeRoles:
                roleManager.removeRoleFromPrincipal(role, self.id)
            # get roles to add and then add them
            addRoles = list(set(roles).difference(set(origRoles)))
            for role in addRoles:
                roleManager.assignRoleToPrincipal(role, self.id)

        # we're not managing domains right now
        if domains:
            msg = 'Zenoss does not currently manage domains for users.'
            raise NotImplementedError(msg)

        # update Zenoss user folder settings
        if REQUEST:
            kw = REQUEST.form
        self.updatePropsFromDict(kw)

        # update password info
        userManager = self.acl_users.userManager
        if password:
            if password != sndpassword:
                if REQUEST:
                    REQUEST['message'] = "Passwords didn't match! No change. "
                    return self.callZenScreen(REQUEST)
                else:
                    raise ValueError("Passwords don't match")
            else:
                userManager.updateUserPassword(self.id, password)
                loggedInUser = REQUEST['AUTHENTICATED_USER']
                # we only want to log out the user if it's *their* passowrd
                # they've changed, not, for example, if the admin user is
                # changing another user's password
                if loggedInUser.getUserName() == self.id:
                    self.acl_users.logout(REQUEST)

        # finish up
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)
        else:
            return user

    security.declareProtected('Change Settings', 'manage_addActionRule')
    def manage_addActionRule(self, id=None, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            ar = ActionRule(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()
            userid = user.getId()
            if userid != self.id:
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def getActionRules(self):
        return self.objectValues(spec=ActionRule.meta_type)

    security.declareProtected('Change Settings', 'manage_addCustomEventView')
    def manage_addCustomEventView(self, id=None, REQUEST=None):
        """Add an action rule to this object.
        """
        if id:
            ar = CustomEventView(id)
            self._setObject(id, ar)
            ar = self._getOb(id)
            user = getSecurityManager().getUser()
            userid = user.getId()
            if userid != self.id:
                userid = self.id
                user = self.getUser(userid)
                ar.changeOwnership(user)
                ar.manage_setLocalRoles(userid, ("Owner",))
        if REQUEST:
            return self.callZenScreen(REQUEST)

    
    #security.declareProtected('Change Settings', 'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, name, type='device', REQUEST=None):
        "Add a Admin Role to this device"
        mobj = None
        if type == 'device':
            mobj =self.getDmdRoot("Devices").findDevice(name)
        else:
            try:
                root = type.capitalize()+'s'
                mobj = self.getDmdRoot(root).getOrganizer(name)
            except KeyError: pass        
        if not mobj:
            if REQUEST:
                REQUEST['message'] = "%s %s not found"%(type.capitalize(),name)
                return self.callZenScreen(REQUEST)
            else: return
        roleNames = [ r.id for r in mobj.adminRoles() ]
        if self.id in roleNames:
            if REQUEST:
                REQUEST['message'] = "Role exists on %s %s" % (type, name)
                return self.callZenScreen(REQUEST)
            else: return
        if name.startswith('/'):
            ar = DevOrgAdministrativeRole(self.id)
        else:
            ar = DeviceAdministrativeRole(self.id)
        if self.defaultAdminRole:
            ar.role = self.defaultAdminRole
            ar.level = self.defaultAdminLevel
        mobj.adminRoles._setObject(self.id, ar)
        ar = mobj.adminRoles._getOb(self.id)
        ar.userSetting.addRelation(self)
        if REQUEST:
            REQUEST['message'] = "Administrative Role Added for %s" % name
            return self.callZenScreen(REQUEST)


    #security.declareProtected('Change Settings','manage_editAdministrativeRoles')
    def manage_editAdministrativeRoles(self, ids=(), role=(), level=(), REQUEST=None):
        """Edit list of admin roles.
        """
        if type(ids) in types.StringTypes:
            ids = [ids]
            level = [level]
            role = [role]
        for ar in self.adminRoles():
            try: i = ids.index(ar.managedObjectName())
            except ValueError: continue
            if ar.role != role[i]: ar.role = role[i]
            if ar.level != level[i]: ar.level = level[i]
        if REQUEST:
            if ids:
                REQUEST['message'] = "Administrative Roles Updated"
            return self.callZenScreen(REQUEST)
        

    #security.declareProtected('Change Settings','manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        import types
        if type(delids) in types.StringTypes:
            delids = [delids]
        for ar in self.adminRoles():
            if ar.managedObjectName() in delids:
                ar.userSetting.removeRelation()
                mobj = ar.managedObject().primaryAq()
                mobj.adminRoles._delObject(ar.id)
        if REQUEST:
            if delids:
                REQUEST['message'] = "Administrative Roles Deleted"
            return self.callZenScreen(REQUEST)
                          
    security.declareProtected('Change Settings', 'manage_emailTest')
    def manage_emailTest(self, REQUEST=None):
        ''' Send a test email to the given userid.
        '''
        destSettings = self.getUserSettings(self.getId())
        destAddress = destSettings.email
        msg = None
        if destAddress:
            fqdn = socket.getfqdn()
            thisUser = self.getUser()
            srcId = thisUser.getId()
            srcSettings = self.getUserSettings(srcId)
            srcAddress = srcSettings.email or 'zenossuser_%s@%s' % (srcId, fqdn)
            # Read body from file probably
            body = ('This is a test message sent by %s' % srcId +
                    ' from the Zenoss installation on %s.' % fqdn)
            emsg = MIMEText(body)
            emsg['Subject'] = 'Zenoss Email Test'
            emsg['From'] = srcAddress
            emsg['To'] = destAddress
            emsg['Date'] = DateTime().rfc822()
            result, errorMsg = Utils.sendEmail(emsg, self.dmd.smtpHost, 
                                self.dmd.smtpPort,
                                self.dmd.smtpUseTLS, self.dmd.smtpUser,
                                self.dmd.smtpPass)
            if result:
                msg = 'Test email sent to %s' % destAddress
            else:
                msg = 'Test failed: %s' % errorMsg
        else:
            msg = 'Test email not sent, user has no email address.'
        if REQUEST:
            REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)
        else:
            return msg


    security.declareProtected('Change Settings', 'manage_pagerTest')
    def manage_pagerTest(self, REQUEST=None):
        ''' Send a test page 
        '''
        destSettings = self.getUserSettings(self.getId())
        destPager = destSettings.pager
        msg = None
        if destPager:
            fqdn = socket.getfqdn()
            srcId = self.getUser().getId()
            msg = ('Test sent by %s' % srcId + 
                    ' from the Zenoss installation on %s.' % fqdn)
            result, errorMsg = Utils.sendPage(destPager, msg, 
                                    self.dmd.snppHost, self.dmd.snppPort)
            if result:
                msg = 'Test page sent to %s' % settings.pager
            else:
                msg = 'Test failed: %s' % errorMsg
        else:
            msg = 'Test page not sent, user has no pager number.'
        if REQUEST:
            REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)
        else:
            return msg

InitializeClass(UserSettingsManager)
InitializeClass(UserSettings)
