import logging
log = logging.getLogger("zen.ZenossInfo")

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo

from Products.ZenModel.version import Current

def manage_addZenossInfo(context, id='ZenossInfo', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    context._setObject(id, about)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() +'/manage_main')

class ZenossInfo(SimpleItem):

    security = ClassSecurityInfo()

    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        return Current.getVersions()
    security.declareProtected('View','getAllVersions')

InitializeClass(ZenossInfo)
