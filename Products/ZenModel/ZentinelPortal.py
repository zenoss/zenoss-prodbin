##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


""" Portal class

$Id: ZentinelPortal.py,v 1.17 2004/04/08 15:35:25 edahl Exp $
"""

import urllib, urlparse
import re
import textwrap

import Globals

from zExceptions import Redirect
from AccessControl import getSecurityManager, ClassSecurityInfo

from Products.Sessions.BrowserIdManager import constructBrowserIdManager
from Products.Sessions.SessionDataManager import constructSessionDataManager

from Products.CMFCore.PortalObject import PortalObjectBase
from Products.CMFCore.utils import getToolByName

from Products.Zuul.interfaces import ICatalogTool
from Products.ZenUtils import Security, Time
from Products.ZenUtils.Utils import prepId
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUI3.browser.interfaces import IErrorMessage

from ZenossSecurity import *

from Products.AdvancedQuery import MatchGlob, Eq, Or

class ZentinelPortal ( PortalObjectBase ):
    """
    The *only* function this class should have is to help in the setup
    of a new ZentinelPortal. It should not assist in the functionality at all.
    """
    meta_type = 'ZentinelPortal'

    _properties = (
        {'id':'title', 'type':'string'},
        {'id':'description', 'type':'text'},
        )
    title = ''
    description = ''

    security = ClassSecurityInfo()

    def __init__( self, id, title='' ):
        PortalObjectBase.__init__( self, id, title )

    def server_time(self):
        return Time.isoDateTime()

    def _additionalQuery(self):
        return None

    def getLoginMessage(self):
        WIDTH = 27
        DELIMITER = "<br />"

        request = self.REQUEST
        session = self.session_data_manager.getSessionData()

        url = request.form.get('came_from')

        if 'terms' in url:
            msg = "You did not accept the Zenoss Terms."
        elif session.get('login_message'):
            msg = session.get('login_message')
            del session['login_message']
        elif 'submitted' in url:
            msg = "Your session has expired, or the entered password, or " \
                  "the username is incorrect."
        else:
            msg = ""

        return DELIMITER.join(textwrap.wrap(msg, WIDTH))

    security.declareProtected(ZEN_COMMON, 'searchDevices')
    @deprecated
    def searchDevices(self, queryString='', REQUEST=None):
        """Returns the concatenation of a device name, ip and mac
        search on the list of devices.
        """
        # TODO: Remove. Not used anymore in Zenoss code --Ian
        zcatalog = self.dmd.Devices.deviceSearch
        glob = queryString.rstrip('*') + '*'
        idGlob = MatchGlob('id', glob)
        titleGlob = MatchGlob('titleOrId', glob)
        idOrTitleQuery = Or(idGlob,titleGlob)
        query = Or(idOrTitleQuery, Eq('getDeviceIp', queryString))
        additionalQuery = self._additionalQuery()
        if additionalQuery:
            query = And( query, additionalQuery )
        brains = zcatalog.evalAdvancedQuery(query)
        if REQUEST and len(brains) == 1:
            raise Redirect(urllib.quote(brains[0].getPrimaryId))
        if additionalQuery:
            idGlob = And( idGlob, additionalQuery )
        brains += self.dmd.Networks.ipSearch.evalAdvancedQuery(idGlob)
        return [ b.getObject() for b in brains ]

    security.declareProtected(ZEN_COMMON, 'searchComponents')
    @deprecated
    def searchComponents(self, device='', component='', REQUEST=None):
        """
        Redirect to the component of a device. Hopefully.
        """
        # TODO: Remove. Not used anymore in Zenoss code --Ian
        catalog = self.dmd.Devices.componentSearch
        brains = []
        if device and component:
            brains = catalog(getParentDeviceName=device)
        matchingBrains = []
        if brains:
            component = prepId(component)
            for brain in brains:
                if brain.getPath().split('/')[-1]==component:
                    if REQUEST:
                        raise Redirect(urllib.quote(
                            brain.getPath()+'/viewEvents'))
                    else:
                        matchingBrains.append(brain)
            if REQUEST and len(matchingBrains) == 0:
                return self.searchDevices(device, REQUEST)
        return [b.getObject() for b in matchingBrains]

    security.declareProtected(ZEN_COMMON, 'dotNetProxy')
    def dotNetProxy(self, path='', params={}, REQUEST=None):
        """
        Logs in to Zenoss.net using the user's credentials and retrieves data,
        thereby putting it in the current domain
        """
        session = self.dmd.ZenUsers.getUserSettings().getDotNetSession()
        response = session.open(path.lstrip('/'))
        if response:
            data = response.read()
            headers = response.headers.dict
            url = response.geturl()
            response.close()
        else:
            return response
        localbase = 'http://localhost:8080/zport/dotNetProxy?path='
        allrefs = re.compile(r"""(href *= *["']|src *= *["'])(.*?)(["'])""")
        proxyrefs = re.compile(
            r"""((<a[^<>]*?|location\.)href *= *["'])(.*?)(['"])""")

        def mod_rewrite(matchobj):
            start, path, end = matchobj.groups()
            if not path.startswith('javascript'):
                path = urlparse.urljoin(url, path)
            return start + path + end

        def make_proxied(matchobj):
            start, trash, path, end = matchobj.groups()
            path = path.replace(session.base_url, localbase)
            return start + path + end

        data = re.sub(allrefs, mod_rewrite, data)
        data = re.sub(proxyrefs, make_proxied, data)
        for header in headers:
            REQUEST.RESPONSE.setHeader(header, headers[header])
        return data

    def isManager(self, obj=None):
        """
        Return true if user is authenticated and has Manager role.
        """
        user = self.dmd.ZenUsers.getUser()
        if user:
            return user.has_role((MANAGER_ROLE, ZEN_MANAGER_ROLE), obj)


    def has_role(self, role, obj=None):
        """Check to see of a user has a role.
        """
        if obj is None: obj = self
        user = getSecurityManager().getUser()
        if user: return user.has_role(role, obj)


    def has_permission(self, perm, obj=None):
        """Check to see of a user has a permission.
        """
        if obj is None: obj = self
        user = getSecurityManager().getUser()
        if user: return user.has_permission(perm, obj)

    def getZenossVersionShort(self):
        return self.About.getZenossVersionShort()

    def getVersionedResourcePath(self, path):
        from Products.ZenUI3.browser.javascript import getVersionedPath
        return getVersionedPath(path)

    def getLoginButton(self):
        return """<input id="loginButton" type="submit" name="submitbutton"
                class="submitbutton" value=""/>"""

    def getExtraLoginFormContents(self):
        """
        On first run, log us in as admin automatically.

        This is done via a proxy form with hidden fields, so that the browser
        doesn't ask to save the password (which will be changed on the next
        screen).
        """
        if not self.dmd._rq:
            return """
            <form id="_proxy_form">
            <input type="hidden" name="__ac_name"/>
            <input type="hidden" name="__ac_password"/>
            <input type="hidden" name="came_from" value="/zport/dmd/quickstart"/>
            </form>
            <script>
            var origform=document.forms[0];
            var newform = document.getElementById('_proxy_form');
            newform.__ac_name.value = 'admin';
            newform.__ac_password.value = 'zenoss';
            newform.action = origform.action;
            newform.method = origform.method;
            newform.submit()
            </script>
            """


Globals.InitializeClass(ZentinelPortal)


class PortalGenerator:

    klass = ZentinelPortal

    def setupTools(self, p):
        """Set up initial tools"""
        addCMFCoreTool = p.manage_addProduct['CMFCore'].manage_addTool
        addCMFCoreTool('CMF Skins Tool', None)


    def setupMailHost(self, p):
        p.manage_addProduct['MailHost'].manage_addMailHost(
            'MailHost', smtp_host='localhost')


    def setupUserFolder(self, p):
        #p.manage_addProduct['OFSP'].manage_addUserFolder()
        Security.createPASFolder(p)
        Security.setupPASFolder(p)


    def setupCookieAuth(self, p):
        # XXX PAS is handling this now, right?
        #p.manage_addProduct['CMFCore'].manage_addCC(
        #    id='cookie_authentication')
        pass


    def setupRoles(self, p):
        # Set up the suggested roles.
        p.__ac_roles__ += (ZEN_USER_ROLE, ZEN_MANAGER_ROLE,)


    def setupPermissions(self, p):
        # Set up some suggested role to permission mappings.
        mp = p.manage_permission
        mp(ZEN_CHANGE_SETTINGS,[ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_CHANGE_DEVICE, [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_CHANGE_DEVICE_PRODSTATE,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_MANAGE_DMD, [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_DELETE, [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_DELETE_DEVICE, [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_ADD, [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_VIEW, [ZEN_USER_ROLE, ZEN_MANAGER_ROLE,
                        MANAGER_ROLE, OWNER_ROLE])
        mp(ZEN_COMMON, ["Authenticated", ZEN_USER_ROLE, ZEN_MANAGER_ROLE,
                        MANAGER_ROLE, OWNER_ROLE], 1)

        # Events
        mp(ZEN_MANAGE_EVENTMANAGER,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_MANAGE_EVENTS,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)
        mp(ZEN_SEND_EVENTS,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)

        mp(ZEN_CHANGE_ALERTING_RULES,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)
        mp(ZEN_CHANGE_ADMIN_OBJECTS, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_CHANGE_EVENT_VIEWS, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_ADMIN_DEVICE, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_MANAGE_DEVICE, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_ZPROPERTIES_EDIT, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_ZPROPERTIES_VIEW,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, ZEN_USER_ROLE], 1)
        mp(ZEN_EDIT_LOCAL_TEMPLATES, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_RUN_COMMANDS, [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_DEFINE_COMMANDS_EDIT, [MANAGER_ROLE], 1)
        mp(ZEN_DEFINE_COMMANDS_VIEW,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, ZEN_USER_ROLE], 1)
        mp(ZEN_MAINTENANCE_WINDOW_EDIT, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_MAINTENANCE_WINDOW_VIEW,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, ZEN_USER_ROLE], 1)
        mp(ZEN_ADMINISTRATORS_EDIT, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        mp(ZEN_ADMINISTRATORS_VIEW,
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, ZEN_USER_ROLE], 1)
        #mp(ZEN_EDIT_USER, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        #mp(ZEN_EDIT_USERGROUP, [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)

    def setupDefaultSkins(self, p):
        from Products.CMFCore.DirectoryView import addDirectoryViews
        ps = getToolByName(p, 'portal_skins')
        addDirectoryViews(ps, 'skins', globals())
        ps.manage_addProduct['OFSP'].manage_addFolder(id='custom')
        ps.addSkinSelection('Basic', "custom, zenmodel", make_default=1)
        p.setupCurrentSkin()


    def setupSessionManager(self, p):
        """build a session manager and brower id manager for zport"""
        constructBrowserIdManager(p, cookiepath="/zport")
        constructSessionDataManager(p, "session_data_manager",
                    title="Session Data Manager",
                    path='/temp_folder/session_data')


    def setup(self, p, create_userfolder):
        if create_userfolder:
            self.setupUserFolder(p)
        #self.setupCookieAuth(p)
        self.setupTools(p)
        self.setupMailHost(p)
        self.setupRoles(p)
        self.setupPermissions(p)
        self.setupDefaultSkins(p)
        self.setupSessionManager(p)


    def create(self, parent, id, create_userfolder):
        id = str(id)
        portal = self.klass(id=id)
        parent._setObject(id, portal)
        # Return the fully wrapped object.
        p = parent.this()._getOb(id)
        self.setup(p, create_userfolder)
        return p


    def setupDefaultProperties(self, p, title, description,
                               email_from_address, email_from_name,
                               validate_email,
                               ):
        p._setProperty('email_from_address', email_from_address, 'string')
        p._setProperty('email_from_name', email_from_name, 'string')
        p._setProperty('validate_email', validate_email and 1 or 0, 'boolean')
        p.title = title
        p.description = description


manage_addZentinelPortal = Globals.HTMLFile('dtml/addPortal', globals())
manage_addZentinelPortal.__name__ = 'addPortal'

def manage_addZentinelPortal(obj, id="zport", title='Zentinel Portal',
                         description='',
                         create_userfolder=True,
                         email_from_address='postmaster@localhost',
                         email_from_name='Portal Administrator',
                         validate_email=0, RESPONSE=None):
    '''
    Adds a portal instance.
    '''
    gen = PortalGenerator()
    from string import strip
    id = strip(id)
    p = gen.create(obj, id, create_userfolder)
    gen.setupDefaultProperties(p, title, description,
                               email_from_address, email_from_name,
                               validate_email)
    if RESPONSE is not None:
        RESPONSE.redirect(obj.absolute_url()+'/manage_main')
