###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from itertools import chain
import re
import zope.interface
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from Products.Five.viewlet import viewlet

from interfaces import INavigationItem
from manager import SecondaryNavigationManager

class PrimaryNavigationMenuItem(viewlet.ViewletBase):
    zope.interface.implements(INavigationItem)

    template = ViewPageTemplateFile('nav_item.pt')

    url = ''
    target = '_self'
    active_class = 'active'
    inactive_class = 'inactive'
    subviews = ()

    @property
    def title(self):
        return self.__name__

    def update(self):
        super(PrimaryNavigationMenuItem, self).update()
        if isinstance(self.subviews, basestring):
            self.subviews = self.subviews.split()

    @property
    def selected(self):
        requestURL = self.request.getURL().replace('/@@', '/')
        for url in chain((self.url,), self.subviews):
            if re.search(url, requestURL) :
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
        Render the menu item into html.
        This needs to look at the permissions from the perspective
        of the DMD. This way the menu will not change if a user has
        View Permission in one Context but not in another.
        The default zope permissions mechanism only looks at the
        permissions from the current context.
        """
        # empty permissions list means that the permission is either not set
        # or is zope2.Public (everyone can access it)
        if not self.__ac_permissions__:
            return self.template()

        # permissions come from zope looking like
        #     (('ZenCommon', ('', 'update', 'render')),)
        # NOTE: You can only have one permission per nav item
        permission = self.__ac_permissions__[0][0]
        if self.context.dmd.has_permission(permission):
            return self.template()

        # user does not have permission to view the menu item globally
        return ''


class SecondaryNavigationMenuItem(PrimaryNavigationMenuItem):
    zope.interface.implements(INavigationItem)

    parentItem = ""

    @property
    def selected(self):
        requestURL = self.request.getURL().replace('/@@', '/')
        for url in chain((self.url,), self.subviews):
            if re.search(url, requestURL) :
                return True
        return False


