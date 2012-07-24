##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import zope.interface
import zope.component
from zope.viewlet.interfaces import IViewletManager, IViewlet
from zope.contentprovider.interfaces import BeforeUpdateEvent

from Products.Five.viewlet.manager import ViewletManagerBase

from interfaces import IPrimaryNavigationMenu, ISecondaryNavigationMenu


def getWeight((name, viewlet)):
    try:
        return float(viewlet.weight)
    except (AttributeError, ValueError):
        return 0


class WeightOrderedViewletManager(ViewletManagerBase):
    """Weight ordered viewlet managers."""

    def sort(self, viewlets):
        return sorted(viewlets, key=getWeight)



class PrimaryNavigationManager(WeightOrderedViewletManager):
    zope.interface.implements(IPrimaryNavigationMenu)


class SecondaryNavigationManager(WeightOrderedViewletManager):
    """
    A secondary level of navigation.

    Knows how to look up the parent item to see if it is selected.
    """
    zope.interface.implements(ISecondaryNavigationMenu)

    def getViewletsByParentName(self, name):
        if not hasattr(self, 'viewlets'): self.update()
        return [v for v in self.viewlets if v.parentItem==name]

    def getActivePrimaryName(self):
        primary = PrimaryNavigationManager(self.context, self.request,
                                           self.__parent__)
        primary.update()
        for v in primary.viewlets:
            if v.selected: return v.__name__
        return None

    def getActiveViewlets(self):
        viewlets = []
        primaryName = self.getActivePrimaryName()
        if primaryName:
            viewlets = self.getViewletsByParentName(primaryName)
        return viewlets

    def render(self):
        return '\n'.join(v.render() for v in self.getActiveViewlets())
