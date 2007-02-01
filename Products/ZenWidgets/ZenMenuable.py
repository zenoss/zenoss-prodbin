from AccessControl import ClassSecurityInfo
from ZenMenu import ZenMenu
from Globals import InitializeClass
from Acquisition import aq_base, aq_parent, aq_chain
from Products.ZenRelations.RelSchema import *

class ZenMenuable:
    """ ZenMenuable is a mixin providing menuing.
    """

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenu')
    def manage_addZenMenu(self, id=None, desc='', REQUEST=None):
        """ Add a menu item to this device organizer """
        mu = None
        if id:
            mu = ZenMenu(id)
            self.zenMenus._setObject(id, mu)
            if self.meta_type == 'Device':
                self.setLastChange()
            mu.description = desc
        if REQUEST:
            if mu:
                REQUEST['message'] = 'Menu Added'
                url = '%s/zenMenus/%s' % (self.getPrimaryUrlPath(), mu.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return mu

    security.declareProtected('Change Device', 'manage_deleteZenMenu')
    def manage_deleteZenMenu(self, delids=(), REQUEST=None):
        """ Delete Menu Items from this object """
        if isinstance(delids,(str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenus._delObject(id)
        if self.meta_type == 'Device':
            self.setLastChange()
        if REQUEST:
            REQUEST['message'] = "Menu(s) Deleted"
            return self.callZenScreen(REQUEST)
    

    security.declareProtected('View', 'getMenus')
    def getMenus(self, asDict=False):
        """ Get all menus available in this context
            including acquired ones.
        """
        menus = {}
        mychain = aq_chain(self.primaryAq())
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'zenMenus', None):
                for c in obj.zenMenus():
                    menus[c.id] = c
        def cmpMenus(a, b):
            return cmp(a.getId(), b.getId())
        if not asDict:
            menus = menus.values()
            menus.sort(cmpMenus)
        return menus
   

InitializeClass(ZenMenuable)

