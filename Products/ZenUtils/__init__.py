from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# monkey patch PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
from Products.PluggableAuthService import PluggableAuthService
from Security import _createInitialUser
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser

# monkey patches for the PAS login form
from Products.PluggableAuthService.plugins import CookieAuthHelper

def manage_afterAdd(self, item, container):
    """We don't want CookieAuthHelper setting the login attribute, we we'll
    override manage_afterAdd().

    For now, the only thing that manage_afterAdd does is set the login_form
    attribute, but we will need to check this after every upgrade of the PAS.
    """
    pass

CookieAuthHelper.CookieAuthHelper.manage_afterAdd = manage_afterAdd

def login(self):
    """ Set a cookie and redirect to the url that we tried to
    authenticate against originally.
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
    if 'submitted' not in came_from:
        came_from += '?submitted=%s' % submitted
    if self.dmd.acceptedTerms:
        url = came_from
    else:
        url = "%s/zenoss_terms/?came_from=%s" % (self.absolute_url(), came_from)
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
    return response.redirect(url)


CookieAuthHelper.CookieAuthHelper.termsCheck = termsCheck
