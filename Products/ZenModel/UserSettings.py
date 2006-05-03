#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from random import choice

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from AccessControl import getSecurityManager
from Acquisition import aq_base

from Products.ZenEvents.ActionRule import ActionRule
from Products.ZenEvents.CustomEventView import CustomEventView

from ZenModelRM import ZenModelRM

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
                , 'permissions'   : (
                  permissions.view, )
                },
            )
         },
        )


    def getAllUserSettings(self):
        """Return list user settings objects.
        """
        return filter(lambda u: u.id != "admin", 
                    self.objectValues(spec="UserSettings"))
            

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


    def getUserSettings(self, userid=None):
        """Return a user folder.  If userid is not passed return current user.
        """
        user=None
        if userid is None:
            user = getSecurityManager().getUser()
            userid = user.getId()
        folder = self._getOb(userid,None)
        if not folder and userid:
            ufolder = UserSettings(userid)
            self._setObject(ufolder.getId(), ufolder)
            folder = self._getOb(userid)
            if not user: user = self.getUser(userid)
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
        self.acl_users._doDelUsers(userids)
        for userid in userids:
            if getattr(aq_base(self), userid, False):
                self._delObject(userid)
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)


    def cleanUserFolders(self):
        """Delete orphaned user folders.
        """
        userfolders = self._getOb(UserFolderId)
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
    oncallStart = 0
    oncallEnd = 0
    escalationMinutes = 0

    _properties = ZenModelRM._properties + (
        {'id':'email', 'type':'string', 'mode':'w'},
        {'id':'pager', 'type':'string', 'mode':'w'},
        {'id':'defaultPageSize', 'type':'int', 'mode':'w'},
        {'id':'defaultEventPageSize', 'type':'int', 'mode':'w'},
        {'id':'oncallStart', 'type':'int', 'mode':'w'},
        {'id':'oncallEnd', 'type':'int', 'mode':'w'},
        {'id':'escalationMinutes', 'type':'int', 'mode':'w'},
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
        user = self.getUser(self.id)
        if not user: 
            if REQUEST: 
                REQUEST['message'] = "user %s not found" % self.id
                return self.callZenScreen(REQUEST)
            else: 
                return
        if password and password != sndpassword:
            if REQUEST: 
                REQUEST['message'] = "Passwords didn't match no change: "
                return self.callZenScreen(REQUEST)
            else:
                raise ValueError("Passwords don't match")
        if not password: password = user._getPassword()
        if not roles: roles = user.roles
        if not domains: domains = user.domains
        self.acl_users._doChangeUser(self.id,password,roles,domains)
        if REQUEST: kw = REQUEST.form
        self.updatePropsFromDict(kw)
        if REQUEST:
            REQUEST['message'] = "User saved at time:"
            return self.callZenScreen(REQUEST)
        else:
            return user


    security.declareProtected('Change Settings', 'manage_addActionRule')
    def manage_addActionRule(self, id, REQUEST=None):
        """Add an action rule to this object.
        """
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


    security.declareProtected('Change Settings', 'manage_addCustomEventView')
    def manage_addCustomEventView(self, id, REQUEST=None):
        """Add an action rule to this object.
        """
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


InitializeClass(UserSettingsManager)
InitializeClass(UserSettings)
