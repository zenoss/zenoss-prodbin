###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from itertools import chain
import zope.interface
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.Five.viewlet import viewlet

from interfaces import INavigationItem
from manager import SecondaryNavigationManager

class PrimaryNavigationMenuItem(viewlet.ViewletBase):
    zope.interface.implements(INavigationItem)

    template = ViewPageTemplateFile('nav_item.pt')

    url = ''
    active_class = 'active'
    inactive_class = 'inactive'

    @property
    def title(self):
        return self.__name__

    @property
    def selected(self):
        requestURL = self.request.getURL()
        if requestURL.endswith(self.url):
            return True
        sec = SecondaryNavigationManager(self.context, self.request,
                                         self.__parent__)
        if sec:
            for v in sec.getViewletsByParentName(self.__name__):
                if v.selected:
                    return True
        return False

    @property
    def css(self):
        if self.selected:
            return self.active_class
        else:
            return self.inactive_class

    def render(self):
        """
        Render the menu item into html
        """
        return self.template()


class SecondaryNavigationMenuItem(PrimaryNavigationMenuItem):
    zope.interface.implements(INavigationItem)

    parentItem = ""
    subviews = ()

    def update(self):
        super(SecondaryNavigationMenuItem, self).update()
        if isinstance(self.subviews, basestring):
            self.subviews = [self.subviews]

    @property
    def selected(self):
        requestURL = self.request.getURL()
        for url in chain((self.url,), self.subviews):
            if requestURL.endswith(url) or (url + '/') in requestURL :
                return True
        return False


