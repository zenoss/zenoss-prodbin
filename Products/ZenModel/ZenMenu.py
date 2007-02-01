################################################################################
#
#     Copyright (c) 2007 Zenoss, Inc.
#
################################################################################


from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from ZenMenuItem import ZenMenuItem
from Products.ZenRelations.RelSchema import *
from AccessControl import ClassSecurityInfo
import logging
log = logging.getLogger("zen.Menu")


class ZenMenu(ZenModelRM):
    """ A Menu object that holds Menu Items. 
    """
    
    meta_type = 'ZenMenu'
    description = ""
    
    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    zenRelationsBaseModule = 'Products.ZenWidgets'
    _relations =  (
        ("zenMenuItems", ToManyCont(ToOne, 'ZenMenuItem', 'zenMenus')),
        ("zenMenuables", ToOne(ToManyCont, 'ZenMenuable', 'zenMenus')),
        ) 

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'manage_addZenMenuItem')
    def manage_addZenMenuItem(self, id=None, desc='', action='', REQUEST=None):
        """ Add a menu item to a menu """
        mi = None
        if id:
            mi = ZenMenuItem(id)
            self.zenMenuItems._setObject(id, mi)
            mi.description = desc
            mi.action = action
        return mi
 
    security.declareProtected('Change Device', 'manage_deleteZenMenuItem')
    def manage_deleteZenMenuItem(self, delids=(), REQUEST=None):
        """ Delete Menu Items """
        if isinstance(delids, (str,unicode)): delids = [delids]
        for id in delids:
            self.zenMenuItems._delObject(id)
        

    security.declareProtected('View', 'getMenuHtml')
    def getMenuHtml(self):
        def _tag(tagname, content, **kwargs):
            attrs = ['%s="%s"' % (x, kwargs[x]) for x in kwargs.keys()]
            html = '<%s %s>%s</%s>' % (tagname, ' '.join(attrs).replace(
                                                    'klass','class'), 
                                      content, tagname)
            return html
        menuitems = self.getMenuItems()
        lis = [_tag('li', x.description, 
                action=x.action)
               for x in menuitems]
        html = _tag('ul', '\n'.join(lis),
                    klass='zenMenu',
                    id="menu_%s" % self.id
                   )
        return html

InitializeClass(ZenMenu)

