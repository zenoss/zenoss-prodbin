import zope.interface
from zope.viewlet.interfaces import IViewletManager, IViewlet

class IPrimaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """

class ISecondaryNavigationMenu(IViewletManager):
    """
    Navigation menu viewlet manager.
    """

class INavigationItem(IViewlet):
    """
    A navigable item.
    """
