from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from ZenMenu import ZenMenu
from Globals import InitializeClass
from Acquisition import aq_base, aq_parent, aq_chain
from Products.ZenRelations.RelSchema import *
from zExceptions import NotFound


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

    security.declareProtected('Change Device', 'manage_addItemsToZenMenu')
    def manage_addItemsToZenMenu(self, menuid, items=[{}]):
        """ Add ZenMenuItems to a ZenMenu. 
            Accepts a list of dictionaries.
            Available keyword args:
              id
              description
              action
              permissions
              isglobal
              banned_classes
              allowed_classes
        """
        menu = getattr(self.zenMenus, menuid, None)
        if not menu: menu = self.manage_addZenMenu(menuid)
        if type(items)==type({}): items = [items]
        while items:
            menu.manage_addZenMenuItem(**items.pop())
        return menu

    security.declareProtected('Change Device', 'buildMenus')
    def buildMenus(self, menudict={}):
        """ Build menus from a dictionary. """
        menus = menudict.keys()
        while menus:
            menu = menus.pop()
            self.manage_addItemsToZenMenu(menu, menudict[menu])
        
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
    def getMenus(self, menuids=None, context=None):
        """ Build menus for this context, acquiring ZenMenus
            which in turn acquire ZenMenuItems.

            Pass it a menuid for a list of menuitems, 
            a sequence of menuids for a dict of lists of items, 
            or nothing for a dict of all available menus.
        """
        if not context: context=self
        menus = {}
        user = getSecurityManager().getUser()
        if not isinstance(self, ZenMenuable): return None
        if isinstance(menuids, (str,unicode)): menuids=[menuids]
        mychain = aq_chain(context.primaryAq())
        mychain.reverse()
        for obj in mychain:
            if getattr(aq_base(obj), 'zenMenus', None):
                mens = obj.zenMenus()
                while mens:
                    c = mens.pop()
                    if menuids and c.id not in menuids: continue
                    menu = menus[c.id] = menus.get(c.id, {})
                    its = c.zenMenuItems()
                    while its:
                        i = its.pop()
                        def permfilter(p): return user.has_permission(p,self)
                        permok = filter(permfilter,
                            getattr(i,'permissions',('',)))
                        if not permok \
                           or (not getattr(i, 'isglobal', True) and \
                               not context==i.getMenuItemOwner())\
                           or (i.allowed_classes and not \
                              context.__class__.__name__ in i.allowed_classes)\
                           or context.__class__.__name__ in i.banned_classes: 
                            continue
                        menu[i.id] = i
        keys = menus.keys()
        for key in keys:
            menus[key] = menus[key].values()
        if not menus: 
            return None
        elif len(menus.keys())==1: 
            return menus.values()[0]
        else: 
            return menus

InitializeClass(ZenMenuable)

