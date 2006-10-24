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
import os
from Products import ZenModel
from AccessControl.Permissions import view
from Products.PluggableAuthService.plugins import CookieAuthHelper
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
filename = os.path.join(ZenModel.__path__[0], 'skins', 'zenmodel',
    'login_form.pt')
fh = open(filename)
html = fh.read()
fh.close()
CookieAuthHelper.BASIC_LOGIN_FORM = html

def addLoginForm(self):
    login_form = PageTemplateFile(filename, globals(), __name__='login_form')
    login_form.title = 'Login Form'
    login_form.manage_permission(view, roles=['Anonymous'], acquire=1)

CookieAuthHelper.CookieAuthHelper.addLoginForm = addLoginForm

def manage_afterAdd(self, item, container):
    """ Setup tasks upon instantiation """
    if not 'login_form' in self.objectIds():
        addLoginForm(self)

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
    
    came_from = request.form['came_from']
    if 'submitted' not in came_from:
        came_from += '?submitted=%s' % submitted
    return response.redirect(came_from)

CookieAuthHelper.CookieAuthHelper.login = login
