##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


'''
This module contains monkey patches we needed to make to PAS when we switched
from native ZODB-managed authentication to pluggable authentication.

This module needs to be imported by ZenUtils/__init__.py.

Related tickets:
  http://dev.zenoss.org/trac/ticket/379
  http://dev.zenoss.org/trac/ticket/402
  http://dev.zenoss.org/trac/ticket/443
  http://dev.zenoss.org/trac/ticket/1042
  http://dev.zenoss.org/trac/ticket/4225
  http://jira.zenoss.com/jira/browse/ZEN-110
'''

import urllib
import urlparse
from uuid import uuid1
from cgi import parse_qs
from Acquisition import aq_base
from AccessControl.SpecialUsers import emergency_user
from zope.event import notify
from Products.PluggableAuthService import PluggableAuthService
from Products.PluggableAuthService.plugins import CookieAuthHelper
from Products.PluggableAuthService.interfaces.authservice import _noroles
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.events import UserLoggedInEvent, UserLoggedOutEvent
from Products.ZenUtils.Security import _createInitialUser

# monkey patch PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser

# Monkey patch PAS to monitor logouts (credential resets).
# Have to check the request object to determine when we have an actual
# logout instead of 'fake' logout (like the logout of the anonymous user)
_originalResetCredentials = pas.resetCredentials
def _resetCredentials(self, request, response=None):
    audit("UI.Authentication.Logout")
    notify(UserLoggedOutEvent(self.zport.dmd.ZenUsers.getUserSettings()))
    try:
        _originalResetCredentials(self, request, response)
    except KeyError:
        # see defect ZEN-2942 If the time changes while the server is running
        # set the session database to a sane state.
        ts = self.unrestrictedTraverse('/temp_folder/session_data')
        ts._reset()
        _originalResetCredentials(self, request, response)


pas.resetCredentials = _resetCredentials


def get_ip(request):
    if "HTTP_X_FORWARDED_FOR" in request.environ:
        # Virtual host
        # This can be a comma-delimited list of IPs but we are fine with
        # logging multiple IPs for auditing at this time.
        ip = request.environ["HTTP_X_FORWARDED_FOR"]
    elif "HTTP_HOST" in request.environ:
        # Non-virtualhost
        ip = request.environ["REMOTE_ADDR"]
    else:
        ip = getattr(request, '_client_addr', 'Unknown')

    return ip


# Monkey patch PAS to audit log successful and failed login attempts
def validate(self, request, auth='', roles=_noroles):
    """
    Here is a run down of how this method is called and where it ends up returning
    in various login situations.

    Failure (admin, local, LDAP, and Active Directory)
       is_top=0, user_ids=[], name=login, if not is_top: return None (outside loop)
       is_top=1, user_ids=[], name=login, return anonymous

   Success (admin)
      is_top=0, user_ids=[], name=login, if not is_top: return (outside loop)
      is_top=1, user_ids=[('admin', 'admin')], name=login, if self._authorizeUser(...): return user

    Success (local, LDAP, and Active Directory)
       is_top=0, user_ids=[('username', 'username')], name=login, if self._authorizeUser(...): return user
    """
    plugins = self._getOb( 'plugins' )
    is_top = self._isTop()
    user_ids = self._extractUserIds(request, plugins)
    accessed, container, name, value = self._getObjectContext(request['PUBLISHED'], request)
    ipaddress = get_ip(request)
    for user_id, login in user_ids:
        user = self._findUser(plugins, user_id, login, request=request)
        if aq_base(user) is emergency_user:
            if is_top:
                return user
            else:
                return None

        if self._authorizeUser(user, accessed, container, name, value, roles):
            if name == 'login':
                audit('UI.Authentication.Valid', ipaddress=ipaddress)
                notify(UserLoggedInEvent(self.zport.dmd.ZenUsers.getUserSettings()))
            return user

    if not is_top:
        return None

    anonymous = self._createAnonymousUser(plugins)
    if self._authorizeUser(anonymous, accessed, container, name, value, roles):
        if name == 'login':
            username_ = request.form.get('__ac_name', 'Unknown')
            audit('UI.Authentication.Failed', username_=username_, ipaddress=ipaddress)
        return anonymous

    return None

pas.validate = validate

# monkey patches for the PAS login form

def manage_afterAdd(self, item, container):
    """We don't want CookieAuthHelper setting the login attribute, we we'll
    override manage_afterAdd().

    For now, the only thing that manage_afterAdd does is set the login_form
    attribute, but we will need to check this after every upgrade of the PAS.
    """
    pass

CookieAuthHelper.CookieAuthHelper.manage_afterAdd = manage_afterAdd

def login(self):
    """
    Set a cookie and redirect to the url that we tried to
    authenticate against originally.

    FIXME - I don't think we need this any more now that the EULA is gone -EAD
    """

    request = self.REQUEST
    response = request['RESPONSE']

    login = request.get('__ac_name', '')
    password = request.get('__ac_password', '')
    submitted = request.get('submitted', '')

    pas_instance = self._getPAS()

    if pas_instance is not None:
        pas_instance.updateCredentials(request, response, login, password)

    came_from = request.form.get('came_from') or ''
    if came_from:
        parts = urlparse.urlsplit(came_from)
        querydict = parse_qs(parts[3])
        querydict.pop('terms', None)
        if 'submitted' not in querydict.keys():
            querydict['submitted'] = submitted
        newqs = urllib.urlencode(querydict, doseq=True)
        parts = parts[:3] + (newqs,) + parts[4:]
        came_from = urlparse.urlunsplit(parts)
    else:
        submittedQs = 'submitted=%s' % submitted
        came_from = '/zport/dmd?%s' % submittedQs

    if not self.dmd.acceptedTerms:
        url = "%s/zenoss_terms/?came_from=%s" % (
                    self.absolute_url(), urllib.quote(came_from))
    else:
        url = came_from

    fragment = request.get('fragment', '')
    if fragment:
        fragment = urllib.unquote( fragment)
        if not fragment.startswith( '#'):
            fragment = '#' + fragment
        url += fragment

    if self.dmd.uuid is None:
        self.dmd.uuid = str(uuid1())

    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.login = login


def termsCheck(self):
    """ Check to see if the user has accepted the Zenoss terms.
    """
    request = self.REQUEST
    response = request['RESPONSE']

    acceptStatus = request.form.get('terms') or ''
    url = request.form.get('came_from') or self.absolute_url()

    if acceptStatus != 'Accept':
        self.resetCredentials(request, response)
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += 'terms=Decline'
    else:
        self.dmd.acceptedTerms = True
        self.dmd.uuid = str(uuid1())
    return response.redirect(url)

CookieAuthHelper.CookieAuthHelper.termsCheck = termsCheck
