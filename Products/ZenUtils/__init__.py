from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# monkey path PAS to allow inituser files, but check to see if we need to
# actually apply the patch, first -- support may have been added at some point
from Products.PluggableAuthService import PluggableAuthService
from Security import _createInitialUser
pas = PluggableAuthService.PluggableAuthService
if not hasattr(pas, '_createInitialUser'):
    pas._createInitialUser =  _createInitialUser


