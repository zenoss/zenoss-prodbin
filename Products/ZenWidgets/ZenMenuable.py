from AccessControl import ClassSecurityInfo
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
    def manage_addItemsToZenMenu(self, menuid, items=[()]):
        """ Add ZenMenuItems to a ZenMenu. 
            item is a list of tuples:[(id, description, action)]
        """
        menu = getattr(self.zenMenus, menuid, None)
        if not menu: menu = self.manage_addZenMenu(menuid)
        if type(items)==type(()): items = [items]
        while items:
            menu.manage_addZenMenuItem(*items.pop())
        return menu

    security.declareProtected('Change Device', 'buildMenus')
    def buildMenus(self, menudict={}):
        """ Build menus from a dictionary. """
        menus = menudict.values()
        while menus:
            menu = menudict.pop()
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
    def getMenus(self, menuids=None):
        """ Build menus for this context, acquiring ZenMenus
            which in turn acquire ZenMenuItems.

            Pass it a menuid for a list of menuitems, 
            a sequence of menuids for a dict of lists of items, 
            or nothing for a dict of all available menus.
        """
        menus = {}
        if isinstance(menuids, (str,unicode)): menuids=[menuids]
        mychain = aq_chain(self.primaryAq())
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

    security.declareProtected('View', 'getMenuHtml')
    def getMenuHtml(self, menuid=None):
        def _tag(tagname, content, **kwargs):
            attrs = ['%s="%s"' % (x, kwargs[x]) for x in kwargs.keys()]
            html = '<%s %s>%s</%s>' % (tagname, ' '.join(attrs).replace(
                                                    'klass','class'), 
                                      content, tagname)
            return html
        html = ''
        if menuid:
            menuitems = self.getMenus(menuid)
            if menuitems:
                lis = [_tag('li', x.description or x.id, 
                        action=x.action)
                       for x in menuitems]
                html = _tag('ul', '\n'.join(lis),
                            klass='zenMenu',
                            id="menu_%s" % self.id
                           )
        return html

InitializeClass(ZenMenuable)

