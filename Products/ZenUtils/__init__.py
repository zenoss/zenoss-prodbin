from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# monkey patch PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
from Products.PluggableAuthService import PluggableAuthService
from Security import _createInitialUser
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser

# monkey patch for the PAS login form
import os
from Products import ZenModel
from Products.PluggableAuthService.plugins import CookieAuthHelper
filename = os.path.join(ZenModel.__path__[0], 'skins', 'zenmodel',
    'login_form.pt')
fh = open(filename)
html = fh.read()
fh.close()
CookieAuthHelper.BASIC_LOGIN_FORM = html
